"""LoRA adapter -> merged 16-bit weights, for a vLLM deployment that prefers a
single static model over hot LoRA. Optional; `serve.py` runs LoRA directly.

    bomft merge --adapter a
"""
from __future__ import annotations
from pathlib import Path

from .config import load_config
from .paths import base_model_path, run_dir
from .serve import adapter_path


def merge(adapter: str, config: str | None) -> int:
    from unsloth import FastLanguageModel
    import torch

    cfg = load_config(config or (Path(__file__).parents[1] / "configs" /
                                 f"adapter_{adapter}.yaml"))
    lora_dir = adapter_path(adapter).parent          # runs/adapter_x/<ts>/adapter/..
    out = run_dir() / f"adapter_{adapter}" / "merged-16bit"
    print(f"[merge] base {base_model_path(cfg.model.name)}  + LoRA {lora_dir}  -> {out}")

    model, tok = FastLanguageModel.from_pretrained(
        model_name=str(base_model_path(cfg.model.name)),
        max_seq_length=cfg.model.max_seq_length,
        dtype=torch.bfloat16,
        load_in_4bit=False,
        local_files_only=True,
    )
    model.load_adapter(str(lora_dir), adapter_name="default")
    model.save_pretrained_merged(str(out), tok, save_method="merged_16bit")
    print(f"[merge] wrote {out}")
    return 0
