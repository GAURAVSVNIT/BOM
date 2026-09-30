"""LoRA/QLoRA supervised fine-tuning of the local Qwen3.5 checkpoint on the
prepared FIBC BOM dataset (finetune/data/train.jsonl + val.jsonl).

Trains the model to answer a single-turn conversation:
    system: BOM-engineer role + hard-constraint reminders
    user:   natural-language bag specification (the `instruction` field)
    assistant: the flat BOM CSV (the `output` field)

Loss is computed only on the assistant turn, via trl's SFTConfig(completion_only_loss
=True) against a {"prompt": [...], "completion": [...]} dataset shape (both as
chat-message-dict lists) — trl's SFTTrainer applies the chat template and builds
the completion mask internally from that split. This project originally targeted
trl's older DataCollatorForCompletionOnlyLM class, which no longer exists as of
trl 1.9.2 (confirmed empty on the installed cluster env) — completion_only_loss
is its replacement, and explicitly rejects a flattened text field or a custom
formatting_func, hence the prompt/completion split below rather than pre-rendering
text with tokenizer.apply_chat_template() ourselves.

Run `python prepare_dataset.py` first. Then, on a single 80-94GB GPU (e.g. H100),
the recommended path is plain bf16 LoRA — no quantization, since a frozen bf16
base + LoRA adapters for this model fits well inside 94GB (~30-50GB) and avoids
the small quality cost of QLoRA's 4-bit base:

    python train_qwen_bom.py \
        --base-model /path/to/complete/qwen3.5/checkpoint \
        --output-dir runs/qwen_bom_lora_v1

Pass --load-in-4bit only on a smaller/shared GPU where QLoRA's ~15-25GB footprint
is required.

Requires an actual Qwen3.5 checkpoint (config + tokenizer + weight shards) at
--base-model. The model_weights/ folder in this repo currently ships only
config/tokenizer files, not the safetensors weights, so point --base-model at
wherever the complete checkpoint lives (local dir or a hub repo id) once it is.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import torch
from datasets import load_dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig
from trl import SFTConfig, SFTTrainer

THIS_DIR = Path(__file__).resolve().parent
DATA_DIR = THIS_DIR / "data"

MODEL_CLASSES = {
    "image-text-to-text": AutoModelForImageTextToText,
    "causal-lm": AutoModelForCausalLM,
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base-model", default=str(THIS_DIR.parent / "model_weights"), help="Local dir or hub repo id of the complete Qwen3.5 checkpoint")
    p.add_argument("--model-class", choices=list(MODEL_CLASSES), default="image-text-to-text", help="config.json shows architecture Qwen3_5ForConditionalGeneration (vision-capable); use causal-lm only for a text-only sibling checkpoint")
    p.add_argument("--train-file", default=str(DATA_DIR / "train.jsonl"))
    p.add_argument("--val-file", default=str(DATA_DIR / "val.jsonl"))
    p.add_argument("--output-dir", default=str(THIS_DIR / "runs" / "qwen_bom_lora"))
    p.add_argument("--epochs", type=float, default=3.0)
    p.add_argument("--learning-rate", type=float, default=2e-4)
    p.add_argument("--lr-scheduler-type", default="cosine")
    p.add_argument("--warmup-ratio", type=float, default=0.03)
    p.add_argument("--weight-decay", type=float, default=0.0)
    p.add_argument("--optim", default="adamw_torch_fused", help="Full-precision fused AdamW; only switch to a paged/8-bit optimizer if VRAM is tight")
    p.add_argument("--per-device-batch-size", type=int, default=2, help="Bump this up (e.g. 4-8) if `nvidia-smi` shows headroom on a 94GB card")
    p.add_argument("--grad-accum", type=int, default=8, help="effective batch size = per-device-batch-size * grad-accum (default 16)")
    p.add_argument("--max-seq-len", type=int, default=2048)
    p.add_argument("--attn-implementation", default="sdpa", help="Use 'flash_attention_2' instead if flash-attn is installed on the cluster, for faster/lower-memory attention")
    p.add_argument("--lora-r", type=int, default=32)
    p.add_argument("--lora-alpha", type=int, default=64)
    p.add_argument("--lora-dropout", type=float, default=0.05)
    p.add_argument("--load-in-4bit", action="store_true", help="QLoRA: quantize the frozen base model to 4-bit. Only needed on a smaller/shared GPU — on a single 80GB+ card, omit this for plain bf16 LoRA (better quality, no dequant overhead)")
    p.add_argument("--no-gradient-checkpointing", dest="gradient_checkpointing", action="store_false", help="Disable activation checkpointing for higher throughput once you've confirmed VRAM headroom")
    p.add_argument("--seed", type=int, default=13)
    p.add_argument("--resume-from-checkpoint", default=None)
    return p.parse_args()


def build_prompt_completion_dataset(jsonl_path: str):
    """Split each {"messages": [system, user, assistant], "meta": {...}} record
    (written by prepare_dataset.py) into trl's prompt-completion format: prompt
    is the system+user turns, completion is the assistant turn, both left as
    chat-message-dict lists so SFTTrainer applies the chat template itself.
    completion_only_loss=True (set on SFTConfig in main()) requires exactly this
    shape — it will not accept a flattened "text" field or a formatting_func."""
    ds = load_dataset("json", data_files=jsonl_path, split="train")
    ds = ds.map(
        lambda ex: {"prompt": ex["messages"][:2], "completion": ex["messages"][2:]},
        remove_columns=ds.column_names,
    )
    return ds


def main() -> None:
    args = parse_args()
    torch.manual_seed(args.seed)

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    quant_config = None
    if args.load_in_4bit:
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

    model_cls = MODEL_CLASSES[args.model_class]
    model = model_cls.from_pretrained(
        args.base_model,
        quantization_config=quant_config,
        dtype=torch.bfloat16,
        device_map="auto",
        attn_implementation=args.attn_implementation,
        trust_remote_code=True,
    )
    model.config.use_cache = False

    if args.gradient_checkpointing:
        # Required whenever the base model is frozen (LoRA) and gradient checkpointing
        # is on: without this, the recomputed forward pass has no tensor with
        # requires_grad=True to backprop through, and the trainer fails (or on some
        # versions silently produces zero gradients) partway into the first step.
        # prepare_model_for_kbit_training does this too, but that's only invoked for
        # the --load-in-4bit path, so the plain-bf16-LoRA path needs it called directly.
        model.enable_input_require_grads()

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules="all-linear",
    )

    train_ds = build_prompt_completion_dataset(args.train_file)
    val_ds = build_prompt_completion_dataset(args.val_file)
    effective_batch = args.per_device_batch_size * args.grad_accum
    precision = "4-bit QLoRA base + bf16 LoRA adapters" if args.load_in_4bit else "bf16 LoRA (no quantization)"
    print(f"train examples: {len(train_ds)}, val examples: {len(val_ds)}")
    print(f"precision: {precision} | effective batch size: {effective_batch} | lora r={args.lora_r} alpha={args.lora_alpha}")

    sft_config = SFTConfig(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.per_device_batch_size,
        per_device_eval_batch_size=args.per_device_batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.learning_rate,
        lr_scheduler_type=args.lr_scheduler_type,
        warmup_ratio=args.warmup_ratio,
        weight_decay=args.weight_decay,
        optim=args.optim,
        bf16=True,
        max_length=args.max_seq_len,
        packing=False,  # keep each example's own prompt/completion boundary intact for the completion mask
        completion_only_loss=True,  # requires the prompt/completion dataset shape built above, not a flattened text field
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=3,
        load_best_model_at_end=True,
        gradient_checkpointing=args.gradient_checkpointing,
        gradient_checkpointing_kwargs={"use_reentrant": False} if args.gradient_checkpointing else None,
        report_to="none",
        seed=args.seed,
    )

    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        peft_config=lora_config,
        processing_class=tokenizer,
    )

    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"\nsaved LoRA adapter + tokenizer to {args.output_dir}")


if __name__ == "__main__":
    main()
