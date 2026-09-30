"""Path resolution — environment-driven, works both from a full-repo checkout and
from a standalone `$PROJECT_DIR/finetune/` deployment on the cluster.

    BOM_BASE_MODEL   direct path to the pre-staged HF base model (e.g.
                     $PROJECT_DIR/model_weights).  Takes precedence over
                     BOM_MODEL_DIR/<name>.
    BOM_MODEL_DIR    directory that CONTAINS the base model folder.
    BOM_ROOT         repo root (holds 03_DATASET/, 07_TRAINING/ ...).
                     default: two levels up from this file.
    BOM_DATASET_DIR  the built dataset dir.
                     default: $BOM_ROOT/03_DATASET, else 07_TRAINING/data
                     (populated by hpc/prepare_data.sh), else ../03_DATASET.
    BOM_RUN_DIR      where runs (adapters, logs, reports) are written.
                     default: 07_TRAINING/runs
"""
from __future__ import annotations
import os
from pathlib import Path

_HERE = Path(__file__).resolve()
_TRAIN_DIR = _HERE.parents[1]                   # bomft/ -> 07_TRAINING/
_REPO_ROOT_DEFAULT = _TRAIN_DIR.parent          # -> repo (or $PROJECT_DIR)


def train_dir() -> Path:
    return _TRAIN_DIR


def repo_root() -> Path:
    return Path(os.environ.get("BOM_ROOT", _REPO_ROOT_DEFAULT)).resolve()


def dataset_dir() -> Path:
    env = os.environ.get("BOM_DATASET_DIR")
    if env:
        return Path(env).resolve()
    cand = repo_root() / "03_DATASET"
    if (cand / "adapter_a").is_dir() or (cand / "build" / "rules.py").exists():
        return cand.resolve()
    local = _TRAIN_DIR / "data"                 # hpc/prepare_data.sh target
    if (local / "adapter_a").is_dir():
        return local.resolve()
    return cand.resolve()


def model_path() -> Path:
    """The base model directory (a HF folder with config.json). Required for GPU work."""
    direct = os.environ.get("BOM_BASE_MODEL")
    if direct:
        p = Path(direct).resolve()
    else:
        d = os.environ.get("BOM_MODEL_DIR")
        if not d:
            raise RuntimeError(
                "Set BOM_BASE_MODEL to the base-model path (e.g. "
                "$PROJECT_DIR/model_weights), or BOM_MODEL_DIR to the directory "
                "that contains it.")
        p = (Path(d) / os.environ.get("BOM_MODEL_NAME", "Qwen3-4B-Instruct")).resolve()
    if not (p / "config.json").exists():
        raise FileNotFoundError(f"no HF model at {p} (expected config.json)")
    return p


# kept for callers that pass an explicit name; ignores name when BOM_BASE_MODEL set
def base_model_path(name: str | None = None) -> Path:
    if os.environ.get("BOM_BASE_MODEL"):
        return model_path()
    if name:
        os.environ.setdefault("BOM_MODEL_NAME", name)
    return model_path()


def run_dir() -> Path:
    env = os.environ.get("BOM_RUN_DIR")
    d = Path(env).resolve() if env else (_TRAIN_DIR / "runs")
    d.mkdir(parents=True, exist_ok=True)
    return d


def adapter_jsonl(adapter: str, split: str) -> Path:
    return dataset_dir() / f"adapter_{adapter}" / f"{split}.jsonl"


def eval_real_jsonl() -> Path:
    return dataset_dir() / "eval_real" / "eval_real.jsonl"


def gold_jsonl(layer: str) -> Path:
    return dataset_dir() / "gold" / f"{layer}.jsonl"


def rules_module_path() -> Path:
    return dataset_dir() / "build" / "rules.py"
