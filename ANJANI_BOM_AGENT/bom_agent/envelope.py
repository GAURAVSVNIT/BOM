"""Stage 4 — the rule envelope for this load (plan §2 stage 4, §1.6).

GSM floor + belt band + required belt gramage + mandatory/forbidden component
sets + lamination bands + yarn coefficient + target/tolerance + knob order.
All from 03_DATASET/build/rules.py so it can never drift from the trained data.
"""
from __future__ import annotations

from .rules_registry import rules


def envelope(order_spec: dict, family: str, loop_type: str,
             loop_qty: int | None = 4) -> dict:
    R = rules()
    swl = (order_spec.get("swl_kg") or {}).get("value")
    sf_raw = (order_spec.get("sf") or {}).get("value")
    sfn = int(str(sf_raw).split(":")[0]) if sf_raw else None

    floor = R.gsm_floor(swl, sfn, loop_type) if (swl and sfn) else None
    band = R.belt_band(swl, sfn, loop_type) if (swl and sfn) else None
    req = R.required_belt_gpm(swl, sfn, loop_qty or 4) if (swl and sfn) else None

    return {
        "gsm_floor": floor,
        "gsm_catalogue": list(R.GSM_CATALOGUE),
        "belt_width_mm": band[0] if band else None,
        "belt_gpm_band": [band[1], band[2]] if band else None,
        "belt_gpm_required": round(req, 1) if req else None,
        "belt_gpm_note": "design target, not a hard limit",
        "mandatory_components": R.MANDATORY.get(family, []),
        "forbidden_components": R.FORBIDDEN.get(family, []),
        "lamination_bands": R.LAMINATION_BANDS,
        "yarn_coefficient": R.YARN_COEFF.get(family),
        "target_factor": R.TARGET_FACTOR,
        "tolerance": R.TOLERANCE,
        "solver_knob_order": R.SOLVER_KNOBS,
        "dimension_basis": (R.GEOMETRY.get(family) or {}).get("basis", "EXTERNAL"),
        "interim_chart": family in ("u_panel", "box"),   # plan O1
    }
