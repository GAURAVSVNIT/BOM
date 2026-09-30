"""Pre-run checks. Torch-free parts run on the login node; `assert_gpu_ok`
runs inside every sbatch job before training/serving touches the GPU.
"""
from __future__ import annotations
import os
import sys

from .paths import (dataset_dir, adapter_jsonl, model_path, base_model_path,
                    repo_root, train_dir)


def check_env() -> list[str]:
    problems = []
    if not (os.environ.get("BOM_BASE_MODEL") or os.environ.get("BOM_MODEL_DIR")):
        problems.append("neither BOM_BASE_MODEL nor BOM_MODEL_DIR is set "
                        "(path to the pre-staged base model)")
    else:
        try:
            model_path()
        except Exception as e:
            problems.append(str(e))
    for ad in ("a", "b"):
        for sp in ("train", "val"):
            p = adapter_jsonl(ad, sp)
            if not p.exists():
                problems.append(f"missing dataset file: {p}")
    if os.environ.get("HF_HUB_OFFLINE") != "1":
        problems.append("HF_HUB_OFFLINE != 1  (set it — compute nodes have no network)")
    return problems


def assert_gpu_ok(min_free_gb: int = 36) -> None:
    import torch
    if not torch.cuda.is_available():
        sys.exit("[preflight] CUDA not available")
    name = torch.cuda.get_device_name(0)
    props = torch.cuda.get_device_properties(0)
    free, total = torch.cuda.mem_get_info()
    free_gb = free / 2**30
    print(f"[preflight] GPU: {name}  sm_{props.major}{props.minor}  "
          f"{total/2**30:.0f} GB total, {free_gb:.0f} GB free")
    if not torch.cuda.is_bf16_supported():
        sys.exit("[preflight] bf16 not supported on this device (plan §9.2 needs it)")
    if "H100" not in name and props.major < 9:
        print(f"[preflight] WARNING: expected an H100 (sm_90); got {name}. Continuing.")
    if free_gb < min_free_gb:
        sys.exit(f"[preflight] only {free_gb:.0f} GB free, need >= {min_free_gb}. "
                 f"Is another process on this GPU?")


def main() -> int:
    print(f"[preflight] repo   : {repo_root()}")
    print(f"[preflight] dataset: {dataset_dir()}")
    try:
        print(f"[preflight] model  : {model_path()}")
    except Exception as e:
        print(f"[preflight] model  : {e}")
    problems = check_env()
    # config files parse?
    from .config import load_config
    cfgdir = train_dir() / "configs"
    for name in ("adapter_a.yaml", "adapter_b.yaml", "serve.yaml"):
        try:
            load_config(cfgdir / name)
        except Exception as e:
            problems.append(f"config {name}: {e}")
    # schema builds?
    try:
        from .schema import guided_json
        guided_json("a"); guided_json("b")
    except Exception as e:
        problems.append(f"schema build failed: {e}")

    if problems:
        print("\n[preflight] PROBLEMS:")
        for p in problems:
            print("  -", p)
        return 1
    print("\n[preflight] OK — env, datasets, configs and schemas all resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
