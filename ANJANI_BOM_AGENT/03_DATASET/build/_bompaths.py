# -*- coding: utf-8 -*-
"""
_bompaths.py — portable path resolution for the dataset build pipeline.

Replaces the hard-coded  ROOT = r"C:\\Users\\Nikhil1616\\Desktop\\BOM"  that every
stage used to carry (issue #2 in the repo analysis: "not runnable as shipped").

Resolution order
----------------
ROOT  — project root; holds ``All_Things/`` for stages 00-03
    1. ``$BOM_ROOT``              if set
    2. else the repository root that contains this file
       (``<repo>/03_DATASET/build/_bompaths.py``  ->  ``<repo>``)

OUT   — dataset dir; holds ``sweep.json``, ``gold/``, ``adapter_a/`` ...
    1. ``$BOM_DATASET_DIR``       if set
    2. else ``$ROOT/dataset``     if that directory exists  (original Desktop\\BOM layout)
    3. else ``<repo>/03_DATASET`` (the folder this ``build/`` dir lives in — collected layout)

Both historical layouts therefore keep working with zero configuration, and any
machine can override with two environment variables.
"""
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_DATASET_DIR = os.path.dirname(_HERE)             # <repo>/03_DATASET
_REPO_ROOT = os.path.dirname(_DATASET_DIR)        # <repo>

ROOT = os.path.abspath(os.environ.get("BOM_ROOT", _REPO_ROOT))

if os.environ.get("BOM_DATASET_DIR"):
    OUT = os.path.abspath(os.environ["BOM_DATASET_DIR"])
elif os.path.isdir(os.path.join(ROOT, "dataset")):
    OUT = os.path.join(ROOT, "dataset")          # original  Desktop\BOM\dataset
else:
    OUT = _DATASET_DIR                            # collected ANJANI_BOM_AGENT/03_DATASET

GOLD = os.path.join(OUT, "gold")
os.makedirs(OUT, exist_ok=True)


def p(*parts):
    """Path under the dataset dir."""
    return os.path.join(OUT, *parts)


def r(*parts):
    """Path under the project root."""
    return os.path.join(ROOT, *parts)


if __name__ == "__main__":
    print("ROOT =", ROOT)
    print("OUT  =", OUT)
    print("GOLD =", GOLD)
