from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RULE_DIR = ROOT / "rules"


@dataclass(frozen=True)
class RuleBook:
    hard: dict[str, Any]
    defaults: dict[str, Any]
    heuristics: dict[str, Any]


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_rulebook() -> RuleBook:
    return RuleBook(
        hard=_load_json(RULE_DIR / "hard_constraints.json"),
        defaults=_load_json(RULE_DIR / "defaults.json"),
        heuristics=_load_json(RULE_DIR / "heuristics.json"),
    )


def nearest_approved_width(min_width_cm: float, widths: list[float]) -> float:
    for width in sorted(float(w) for w in widths):
        if width >= min_width_cm:
            return width
    return float(max(widths))
