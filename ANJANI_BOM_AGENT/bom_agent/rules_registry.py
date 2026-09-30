"""Single access point to the rule book and the deterministic renderer.

Both live in 03_DATASET/build/ (`rules.py`, `renderer.py`). Plan §3 wants these
turned into a JSON registry under bom_agent/rules/registry/ — that is Phase 1 of
the build schedule and not done yet, so for now we import the existing modules
and expose them behind this seam. When the JSON registry lands, only this file
changes.
"""
from __future__ import annotations
import importlib.util
import os
import sys
from functools import lru_cache
from pathlib import Path


def _dataset_build_dir() -> Path:
    env = os.environ.get("BOM_DATASET_DIR")
    root = Path(env) if env else Path(__file__).resolve().parents[1] / "03_DATASET"
    return (root / "build").resolve()


@lru_cache(maxsize=1)
def rules():
    d = _dataset_build_dir()
    sys.path.insert(0, str(d))                       # renderer.py does `import rules`
    spec = importlib.util.spec_from_file_location("rules", d / "rules.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("rules", m)
    spec.loader.exec_module(m)
    return m


@lru_cache(maxsize=1)
def renderer():
    rules()                                          # ensure `rules` is importable
    d = _dataset_build_dir()
    spec = importlib.util.spec_from_file_location("renderer", d / "renderer.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


RULE_VERSION = property(lambda self: rules().RULE_VERSION)
