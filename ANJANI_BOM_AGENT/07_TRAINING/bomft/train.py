"""LoRA fine-tuning (plan §9.2). Two backends:

  backend="hf"       peft + trl SFTTrainer — matches the cluster env
                     (torch 2.13 / transformers 5 / peft 0.20 / trl 1.9). DEFAULT.
  backend="unsloth"  Unsloth FastLanguageModel — opt in with `pip install unsloth`
                     and `model.backend=unsloth`.

    python -m bomft.cli train --config configs/adapter_a.yaml
    python finetune.py --adapter b --base-model $BASE_MODEL --output-dir runs/qwen_bom_lora_b_v1

Completion-only loss: the assistant JSON is the only training target
(assistant_only_loss / completion_only_loss on SFTConfig).
"""
from __future__ import annotations
import dataclasses
import json
import time
from pathlib import Path

from .config import Config, to_dict
from .paths import base_model_path, run_dir, train_dir
from .data import build_chat_dataset, build_hf_dataset


def _resolve_out_dir(cfg: Config) -> Path:
    if cfg.train.output_dir:
        d = Path(cfg.train.output_dir)
        if not d.is_absolute():
            d = train_dir() / d
    else:
        d = run_dir() / f"adapter_{cfg.data.adapter}" / time.strftime("%Y%m%d-%H%M%S")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sft_config(SFTConfig, cfg: Config, out_dir: Path, bf16: bool):
    """Build SFTConfig, dropping any kwarg this trl version doesn't know."""
    want = dict(
        output_dir=str(out_dir),
        num_train_epochs=cfg.train.epochs,
        per_device_train_batch_size=cfg.train.per_device_train_batch_size,
        per_device_eval_batch_size=cfg.train.per_device_train_batch_size,
        gradient_accumulation_steps=cfg.train.gradient_accumulation_steps,
        learning_rate=cfg.train.learning_rate,
        lr_scheduler_type=cfg.train.lr_scheduler_type,
        warmup_ratio=cfg.train.warmup_ratio,
        weight_decay=cfg.train.weight_decay,
        max_grad_norm=cfg.train.max_grad_norm,
        optim=cfg.train.optim,
        gradient_checkpointing=cfg.train.gradient_checkpointing,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        bf16=bf16, fp16=not bf16,
        logging_steps=cfg.train.logging_steps,
        eval_strategy="steps", eval_steps=cfg.train.eval_steps,
        save_strategy="steps", save_steps=cfg.train.save_steps,
        save_total_limit=cfg.train.save_total_limit,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss", greater_is_better=False,
        seed=cfg.train.seed,
        report_to=cfg.train.report_to,
        packing=cfg.train.packing,
        # completion-only loss — names have churned across trl versions; keep all,
        # the filter below drops whatever this version lacks
        assistant_only_loss=True,
        completion_only_loss=True,
        max_length=cfg.model.max_seq_length,
        max_seq_length=cfg.model.max_seq_length,
        chat_template_kwargs={"enable_thinking": cfg.model.enable_thinking},
    )
    if cfg.model.backend == "unsloth":
        # build_hf_dataset() pre-renders a `text` column for this backend; the
        # default `hf` backend uses build_chat_dataset()'s `messages` column,
        # which trl auto-detects as conversational — dataset_text_field would
        # make it look for a `text` column that doesn't exist (KeyError).
        want["dataset_text_field"] = "text"
    known = {f.name for f in dataclasses.fields(SFTConfig)}
    dropped = sorted(set(want) - known)
    if dropped:
        print(f"[bomft] SFTConfig: this trl drops {dropped}")
    return SFTConfig(**{k: v for k, v in want.items() if k in known})


def _load_hf(cfg: Config, model_path: Path):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

    tok = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    load_kw = dict(local_files_only=True,
                   attn_implementation=cfg.model.attn_implementation)
    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    if cfg.model.load_in_4bit:
        from transformers import BitsAndBytesConfig
        load_kw["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=dtype, bnb_4bit_use_double_quant=True)
    else:
        # transformers >=5 renamed torch_dtype -> dtype
        load_kw["dtype"] = dtype

    try:
        model = AutoModelForCausalLM.from_pretrained(str(model_path), **load_kw)
    except TypeError:
        load_kw["torch_dtype"] = load_kw.pop("dtype", dtype)
        model = AutoModelForCausalLM.from_pretrained(str(model_path), **load_kw)
    if cfg.model.load_in_4bit:
        model = prepare_model_for_kbit_training(
            model, use_gradient_checkpointing=cfg.train.gradient_checkpointing)
    model.config.use_cache = False

    lc = LoraConfig(r=cfg.lora.r, lora_alpha=cfg.lora.alpha,
                    lora_dropout=cfg.lora.dropout, bias=cfg.lora.bias,
                    target_modules=list(cfg.lora.target_modules),
                    task_type="CAUSAL_LM")
    model = get_peft_model(model, lc)
    model.print_trainable_parameters()
    return model, tok


def _load_unsloth(cfg: Config, model_path: Path):
    from unsloth import FastLanguageModel
    import torch
    model, tok = FastLanguageModel.from_pretrained(
        model_name=str(model_path), max_seq_length=cfg.model.max_seq_length,
        dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
        load_in_4bit=cfg.model.load_in_4bit, local_files_only=True)
    model = FastLanguageModel.get_peft_model(
        model, r=cfg.lora.r, lora_alpha=cfg.lora.alpha, lora_dropout=cfg.lora.dropout,
        target_modules=list(cfg.lora.target_modules), bias=cfg.lora.bias,
        use_gradient_checkpointing="unsloth", random_state=cfg.train.seed,
        max_seq_length=cfg.model.max_seq_length)
    return model, tok


def train(cfg: Config) -> Path:
    import torch
    from trl import SFTConfig, SFTTrainer
    from transformers import EarlyStoppingCallback, set_seed

    from .preflight import assert_gpu_ok
    assert_gpu_ok(min_free_gb=16 if cfg.model.load_in_4bit else 36)
    set_seed(cfg.train.seed)

    out_dir = _resolve_out_dir(cfg)
    (out_dir / "config.resolved.json").write_text(
        json.dumps(to_dict(cfg), indent=2), encoding="utf-8")
    mp = base_model_path(cfg.model.name)
    bf16 = torch.cuda.is_bf16_supported()
    print(f"[bomft] backend={cfg.model.backend}  base={mp}")
    print(f"[bomft] adapter={cfg.data.adapter}  out={out_dir}  bf16={bf16}")

    if cfg.model.backend == "unsloth":
        model, tok = _load_unsloth(cfg, mp)
        train_ds = build_hf_dataset(cfg.data.adapter, cfg.data.train_split, tok,
                                    cfg.data.max_examples, cfg.model.enable_thinking)
        eval_ds = build_hf_dataset(cfg.data.adapter, cfg.data.eval_split, tok,
                                   enable_thinking=cfg.model.enable_thinking)
    else:
        model, tok = _load_hf(cfg, mp)
        train_ds = build_chat_dataset(cfg.data.adapter, cfg.data.train_split,
                                      cfg.data.max_examples)
        eval_ds = build_chat_dataset(cfg.data.adapter, cfg.data.eval_split)
    print(f"[bomft] train {len(train_ds)}  eval {len(eval_ds)}")

    args = _sft_config(SFTConfig, cfg, out_dir, bf16)
    common = dict(model=model, args=args, train_dataset=train_ds, eval_dataset=eval_ds,
                  callbacks=[EarlyStoppingCallback(cfg.train.early_stopping_patience)])
    try:
        trainer = SFTTrainer(processing_class=tok, **common)
    except TypeError:
        trainer = SFTTrainer(tokenizer=tok, **common)

    result = trainer.train()

    adapter_out = out_dir / "adapter"
    trainer.model.save_pretrained(str(adapter_out))
    tok.save_pretrained(str(adapter_out))
    (out_dir / "train_result.json").write_text(
        json.dumps({"metrics": result.metrics,
                    "best_checkpoint": trainer.state.best_model_checkpoint,
                    "best_metric": trainer.state.best_metric},
                   indent=2, default=str), encoding="utf-8")

    latest = out_dir.parent / "latest"
    try:
        if latest.is_symlink() or latest.exists():
            latest.unlink()
        latest.symlink_to(out_dir, target_is_directory=True)
    except OSError:
        (out_dir.parent / "latest.txt").write_text(str(out_dir), encoding="utf-8")

    print(f"[bomft] done. adapter -> {adapter_out}")
    print(f"[bomft] train_loss {result.metrics.get('train_loss')} "
          f"(watch 0.5-1.0; ~0 == memorised, cut r/epochs)")
    return out_dir
