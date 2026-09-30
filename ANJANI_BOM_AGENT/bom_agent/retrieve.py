"""Stage 3 — retrieve the top-k nearest bags the plant has actually built
(plan §2 stage 3). Reads gold/build_spec.jsonl + gold/order_spec.jsonl.

Scoring mirrors 07_adapter_b.retrieve(): geometry distance + SWL distance +
categorical mismatch, hard-filtered to the same family. `product` weighting
(plan C1) is a no-op until product_contents is populated in the data.
"""
from __future__ import annotations
import json
import math
import os
from functools import lru_cache
from pathlib import Path


def _gold_dir() -> Path:
    env = os.environ.get("BOM_DATASET_DIR")
    root = Path(env) if env else Path(__file__).resolve().parents[1] / "03_DATASET"
    return root / "gold"


@lru_cache(maxsize=1)
def _corpus():
    g = _gold_dir()
    order = [json.loads(l) for l in (g / "order_spec.jsonl").open(encoding="utf-8")]
    build = [json.loads(l) for l in (g / "build_spec.jsonl").open(encoding="utf-8")]
    phys = [json.loads(l) for l in (g / "physical_bom.jsonl").open(encoding="utf-8")]
    return order, build, phys


def _dims(o):
    for tag in ("ext", "int"):
        d = [(o.get(f"{tag}_{a}_cm") or {}).get("value") for a in ("L", "W", "H")]
        if all(x is not None for x in d):
            return d
    return None


def retrieve(order_spec: dict, family: str, k: int = 3) -> list[dict]:
    order, build, phys = _corpus()
    e = None
    for tag in ("ext", "int"):
        d = [(order_spec.get(f"{tag}_{a}_cm") or {}).get("value") for a in ("L", "W", "H")]
        if all(x is not None for x in d):
            e = d
            break
    swl = (order_spec.get("swl_kg") or {}).get("value")
    cand = []
    for j, ob in enumerate(order):
        bb = build[j]
        if bb.get("family") != family:
            continue
        e2 = _dims(ob)
        if not e or not e2:
            continue
        geo = math.dist(e, e2) / 100.0
        swl_d = abs((swl or 0) - ((ob.get("swl_kg") or {}).get("value") or 0)) / 1000.0
        score = 0.7 * geo + 0.3 * swl_d
        cand.append((score, j))
    cand.sort()
    out = []
    for score, j in cand[:k]:
        bs = {kk: vv for kk, vv in build[j].items() if not kk.startswith("_")}
        out.append({"similarity": round(1 / (1 + score), 4),
                    "source": build[j].get("_source"),
                    "build_spec": bs,
                    "achieved_weight_g": phys[j].get("grand_total_g")})
    return out
