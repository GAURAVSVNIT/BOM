"""Stage 6 — the deterministic renderer (plan §5). Wraps the existing
03_DATASET/build/renderer.py: BuildSpec + dimensions -> component lines + total.

This is the minimal renderer the dataset ships with (plan §5 / Phase 2 is the
full one). It has geometry for u_panel / box / circular / four_panel(_baffle) /
two_panel / tunnel / container_liner / pinch_corner / platten and returns
(lines, None) for families it cannot yet size.
"""
from __future__ import annotations

from .rules_registry import renderer


def render(build_spec: dict, order_spec: dict) -> dict:
    R = renderer()

    def trip(tag):
        v = [(order_spec.get(f"{tag}_{a}_cm") or {}).get("value") for a in ("L", "W", "H")]
        return v if all(x is not None for x in v) else None

    ext, itn = trip("ext"), trip("int")
    lines, total = R.render(build_spec, ext, itn)
    return {
        "components": lines,
        "grand_total_g": total,
        "renderable": total is not None,
        "dims_used": {"ext": ext, "int": itn},
    }
