"""Typed config: YAML files + ${ENV} expansion + `key=value` CLI overrides.

Usage
-----
    cfg = load_config("configs/adapter_a.yaml", overrides=["train.epochs=3"])
    cfg.model.name            # "Qwen3-4B-Instruct"
    cfg.lora.r                # 16
"""
# NB: no `from __future__ import annotations` here — _from_dict() needs
# field(...).type to be the real class (ModelCfg, LoraCfg, ...) so it can
# recurse. With stringized annotations it would leave nested config as plain
# dicts and `cfg.model.name` would blow up at train time.
import os
import re
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

_ENV = re.compile(r"\$\{([A-Z0-9_]+)(?::-([^}]*))?\}")


def _expand(x: Any) -> Any:
    if isinstance(x, str):
        def sub(m):
            return os.environ.get(m.group(1), m.group(2) if m.group(2) is not None else m.group(0))
        return _ENV.sub(sub, x)
    if isinstance(x, dict):
        return {k: _expand(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_expand(v) for v in x]
    return x


# ── schema ──────────────────────────────────────────────────────────────
@dataclass
class ModelCfg:
    name: str = "Qwen3-4B-Instruct"          # folder under $BOM_MODEL_DIR; ignored
                                             # when $BOM_BASE_MODEL is a direct path
    backend: str = "hf"                      # "hf" = peft + trl (matches the built env:
                                             # torch 2.13 / transformers 5 / trl 1.x).
                                             # "unsloth" needs `pip install unsloth`.
    max_seq_length: int = 2048
    load_in_4bit: bool = False               # plan §9.2: bf16 LoRA. Flip true (QLoRA)
                                             # if an 8-9B base won't fit the GPU shard.
    dtype: str = "bfloat16"
    attn_implementation: str = "sdpa"        # "flash_attention_2" if flash-attn is present
    enable_thinking: bool = False            # Qwen3 thinking models: keep OFF — the
                                             # target is pure JSON, no <think> block


@dataclass
class LoraCfg:
    r: int = 16
    alpha: int = 32
    dropout: float = 0.05
    target_modules: list = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj"])
    bias: str = "none"


@dataclass
class TrainCfg:
    learning_rate: float = 2e-4
    epochs: float = 2.0
    warmup_ratio: float = 0.03
    lr_scheduler_type: str = "cosine"
    per_device_train_batch_size: int = 2
    gradient_accumulation_steps: int = 4
    weight_decay: float = 0.0
    logging_steps: int = 10
    eval_steps: int = 50
    save_steps: int = 50
    save_total_limit: int = 2
    early_stopping_patience: int = 3         # on eval loss
    seed: int = 20260826
    max_grad_norm: float = 1.0
    optim: str = "adamw_torch"               # "paged_adamw_8bit" for QLoRA / tight VRAM (needs bitsandbytes)
    gradient_checkpointing: bool = True
    report_to: str = "none"                  # "tensorboard" if a logdir is wanted
    packing: bool = False                    # completion-only loss, prompt masked
    output_dir: str | None = None            # pin the run dir (e.g. runs/qwen_bom_lora_a_v1);
                                             # None -> runs/adapter_<x>/<timestamp>/


@dataclass
class DataCfg:
    adapter: str = "a"                       # "a" | "b"
    train_split: str = "train"
    eval_split: str = "val"
    # completion-only loss: mask everything up to and including this marker
    response_template: str = "<|im_start|>assistant\n"
    max_examples: int | None = None          # cap for smoke runs


@dataclass
class ServeCfg:
    host: str = "0.0.0.0"
    port: int = 8000
    gpu_memory_utilization: float = 0.90
    max_model_len: int = 4096
    dtype: str = "bfloat16"
    enable_lora: bool = True
    max_loras: int = 2
    max_lora_rank: int = 32
    guided_decoding_backend: str = "xgrammar"


@dataclass
class Config:
    model: ModelCfg = field(default_factory=ModelCfg)
    lora: LoraCfg = field(default_factory=LoraCfg)
    train: TrainCfg = field(default_factory=TrainCfg)
    data: DataCfg = field(default_factory=DataCfg)
    serve: ServeCfg = field(default_factory=ServeCfg)
    run_name: str = "run"


# ── loader ──────────────────────────────────────────────────────────────
def _from_dict(cls, d: dict):
    if not is_dataclass(cls):
        return d
    kw = {}
    known = {f.name: f for f in fields(cls)}
    for k, v in (d or {}).items():
        if k not in known:
            raise KeyError(f"unknown config key '{k}' for {cls.__name__}")
        ftype = known[k].type
        kw[k] = _from_dict(ftype, v) if is_dataclass(ftype) else v
    return cls(**kw)


def _apply_override(cfg: Config, dotted: str) -> None:
    key, _, val = dotted.partition("=")
    if not _:
        raise ValueError(f"override must be key=value, got {dotted!r}")
    node = cfg
    parts = key.split(".")
    for p in parts[:-1]:
        node = getattr(node, p)
    cur = getattr(node, parts[-1])
    # coerce to the current field's type
    if isinstance(cur, bool):
        newv = val.lower() in ("1", "true", "yes")
    elif isinstance(cur, int) and not isinstance(cur, bool):
        newv = int(val)
    elif isinstance(cur, float):
        newv = float(val)
    elif cur is None:
        newv = None if val.lower() in ("none", "null") else val
    else:
        newv = val
    setattr(node, parts[-1], newv)


def load_config(path: str | Path, overrides: list[str] | None = None) -> Config:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    raw = _expand(raw)
    cfg = _from_dict(Config, raw)
    for o in overrides or []:
        _apply_override(cfg, o)
    return cfg


def to_dict(cfg) -> dict:
    if is_dataclass(cfg):
        return {f.name: to_dict(getattr(cfg, f.name)) for f in fields(cfg)}
    if isinstance(cfg, list):
        return [to_dict(x) for x in cfg]
    return cfg
