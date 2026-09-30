#!/usr/bin/env python
"""Top-level fine-tuning entry point (called by hpc/submit_finetune.sh).

    python finetune.py --adapter a \
        --base-model "$PROJECT_DIR/model_weights" \
        --output-dir runs/qwen_bom_lora_a_v1 \
        train.epochs=2

`--adapter a|b` picks configs/adapter_a.yaml or adapter_b.yaml. Any trailing
`key=value` tokens override the config (see bomft/config.py). The base model and
output dir are wired through env + config so bomft/ stays deployment-agnostic.
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser("finetune")
    ap.add_argument("--adapter", choices=["a", "b"], default="a")
    ap.add_argument("--base-model", help="path to the pre-staged HF base model "
                    "(sets $BOM_BASE_MODEL)")
    ap.add_argument("--output-dir", help="pin the run dir, e.g. runs/qwen_bom_lora_a_v1")
    ap.add_argument("--config", help="override the default configs/adapter_<x>.yaml")
    ap.add_argument("--run-dir", help="parent for timestamped runs when --output-dir omitted "
                    "(sets $BOM_RUN_DIR)")
    ap.add_argument("overrides", nargs="*", help="config key=value overrides")
    a = ap.parse_args(argv)

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    if a.base_model:
        os.environ["BOM_BASE_MODEL"] = str(Path(a.base_model).expanduser())
    if a.run_dir:
        os.environ["BOM_RUN_DIR"] = str(Path(a.run_dir).expanduser())

    from bomft.config import load_config
    cfg_path = a.config or (Path(__file__).parent / "configs" / f"adapter_{a.adapter}.yaml")
    overrides = list(a.overrides)
    overrides.append(f"data.adapter={a.adapter}")
    if a.output_dir:
        overrides.append(f"train.output_dir={a.output_dir}")

    cfg = load_config(cfg_path, overrides)
    from bomft.train import train
    out = train(cfg)
    print(f"[finetune] adapter {a.adapter} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
