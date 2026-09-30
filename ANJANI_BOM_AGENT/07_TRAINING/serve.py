#!/usr/bin/env python
"""Top-level serving entry point (called by hpc/submit_serve.sh).

    python serve.py \
        --base-model  "$PROJECT_DIR/model_weights" \
        --adapter-a   runs/qwen_bom_lora_a_v1 \
        --adapter-b   runs/qwen_bom_lora_b_v1 \
        [--print-cmd] [serve.port=8000 ...]

Launches the vLLM OpenAI-compatible server with both LoRA adapters hot and
xgrammar guided-JSON decoding (plan §9.3). Replaces this process with vLLM.
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser("serve")
    ap.add_argument("--base-model")
    ap.add_argument("--adapter-a", help="run dir for adapter A (contains adapter/)")
    ap.add_argument("--adapter-b", help="run dir for adapter B")
    ap.add_argument("--config", default=str(Path(__file__).parent / "configs" / "serve.yaml"))
    ap.add_argument("--print-cmd", action="store_true")
    ap.add_argument("overrides", nargs="*")
    a = ap.parse_args(argv)

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    if a.base_model:
        os.environ["BOM_BASE_MODEL"] = str(Path(a.base_model).expanduser())
    if a.adapter_a:
        os.environ["BOM_ADAPTER_A_DIR"] = str(Path(a.adapter_a).expanduser().resolve())
    if a.adapter_b:
        os.environ["BOM_ADAPTER_B_DIR"] = str(Path(a.adapter_b).expanduser().resolve())

    rest = ["--config", a.config] + (["--print-cmd"] if a.print_cmd else []) + a.overrides
    from bomft.serve import main as serve_main
    return serve_main(rest)


if __name__ == "__main__":
    raise SystemExit(main())
