#!/usr/bin/env python
"""Top-level evaluation entry point (called by hpc/submit_evaluate.sh).

    python evaluate.py \
        --base-model "$PROJECT_DIR/model_weights" \
        --adapter-dir runs/qwen_bom_lora_a_v1 \
        --report-out  data/eval_report_qwen_bom_lora_a_v1.json

Adapter kind (a|b) and eval split are read from
<adapter-dir>/config.resolved.json (written by finetune.py). Structural gates
per plan §10.2; exit code is non-zero on any hard-gate failure.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser("evaluate")
    ap.add_argument("--base-model", help="pre-staged HF base model path (sets $BOM_BASE_MODEL)")
    ap.add_argument("--adapter-dir", required=True,
                    help="a finished run dir (contains adapter/ and config.resolved.json)")
    ap.add_argument("--report-out", required=True)
    ap.add_argument("--adapter", choices=["a", "b"], help="override auto-detection")
    ap.add_argument("--split", help="override (test | val | eval_real)")
    ap.add_argument("--server", help="hit a running vLLM server instead of an in-process engine")
    ap.add_argument("--predictions", help="score a pre-dumped {id,output} JSONL, no model")
    ap.add_argument("--limit", type=int)
    ap.add_argument("overrides", nargs="*",
                    help="config key=value overrides, e.g. serve.gpu_memory_utilization=0.75")
    a = ap.parse_args(argv)

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    if a.base_model:
        os.environ["BOM_BASE_MODEL"] = str(Path(a.base_model).expanduser())

    run = Path(a.adapter_dir).expanduser().resolve()
    resolved = run / "config.resolved.json"
    kind, split, cfg_used = a.adapter, a.split, None
    if resolved.exists():
        rc = json.loads(resolved.read_text())
        kind = kind or rc.get("data", {}).get("adapter")
        split = split or rc.get("data", {}).get("eval_split", "val")
        cfg_used = str(resolved)
    kind = kind or "a"
    split = split or ("eval_real" if kind == "a" else "test")

    # point the serving/engine at THIS adapter dir
    os.environ[f"BOM_ADAPTER_{kind.upper()}_DIR"] = str(run)

    ns = SimpleNamespace(
        adapter=kind, split=split,
        config=str(Path(__file__).parent / "configs" / f"adapter_{kind}.yaml"),
        server=a.server, predictions=a.predictions, limit=a.limit,
        out=str(Path(a.report_out).expanduser()),
        overrides=a.overrides,
    )
    print(f"[evaluate] adapter={kind}  split={split}  dir={run}")
    from bomft.evaluate import run as run_eval
    return run_eval(ns)


if __name__ == "__main__":
    raise SystemExit(main())
