"""`bomft <command>` — one entry point for the whole stack.

  bomft preflight                              env / dataset / config / schema checks
  bomft stats   --adapter a|b                  row counts by split and type
  bomft format  --adapter a --split val -n 2   show formatted chat examples
  bomft schema  --adapter a|b                  print the guided-json schema
  bomft train   --config configs/adapter_a.yaml [key=value ...]      (needs GPU)
  bomft merge   --adapter a|b                  LoRA -> merged 16-bit               (needs GPU)
  bomft serve   [--print-cmd] [key=value ...]  launch vLLM OpenAI server           (needs GPU)
  bomft eval    --adapter a --split test [--server URL | --predictions f.jsonl]
"""
from __future__ import annotations
import argparse
import json
import os
import sys


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(prog="bomft")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("preflight")

    p = sub.add_parser("stats"); p.add_argument("--adapter", choices=["a", "b"], required=True)

    p = sub.add_parser("format")
    p.add_argument("--adapter", choices=["a", "b"], required=True)
    p.add_argument("--split", default="train")
    p.add_argument("-n", "--limit", type=int, default=1)

    p = sub.add_parser("schema"); p.add_argument("--adapter", choices=["a", "b"], required=True)

    p = sub.add_parser("train")
    p.add_argument("--config", required=True)
    p.add_argument("overrides", nargs="*")

    p = sub.add_parser("merge"); p.add_argument("--adapter", choices=["a", "b"], required=True)
    p.add_argument("--config", default=None)

    p = sub.add_parser("serve")
    p.add_argument("--config", default=None)
    p.add_argument("--print-cmd", action="store_true")
    p.add_argument("overrides", nargs="*")

    from .evaluate import build_argparser
    build_argparser(sub.add_parser("eval"))

    a = ap.parse_args(argv)
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    if a.cmd == "preflight":
        from .preflight import main as pf
        return pf()

    if a.cmd == "stats":
        from .data import stats
        print(json.dumps(stats(a.adapter), indent=2))
        return 0

    if a.cmd == "format":
        from .data import iter_examples, render_plain
        for i, ex in enumerate(iter_examples(a.adapter, a.split, a.limit)):
            print(f"\n===== example {i}  ({ex['meta']}) =====")
            print(render_plain(ex))
        return 0

    if a.cmd == "schema":
        from .schema import guided_json
        print(json.dumps(guided_json(a.adapter), indent=2))
        return 0

    if a.cmd == "train":
        from .config import load_config
        from .train import train
        cfg = load_config(a.config, a.overrides)
        train(cfg)
        return 0

    if a.cmd == "merge":
        from .merge_adapter import merge
        return merge(a.adapter, a.config)

    if a.cmd == "serve":
        from .serve import main as serve_main
        rest = []
        if a.config:
            rest += ["--config", a.config]
        if a.print_cmd:
            rest += ["--print-cmd"]
        rest += a.overrides
        return serve_main(rest)

    if a.cmd == "eval":
        from .evaluate import run
        return run(a)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
