"""Stage 7 — the weight solver (plan §6).

Backward mode (a target weight was given): aim at  req_weight_g * 0.99  within
±2%, turning knobs in the engineer's order — belt GPM, then loop cut (free
height), then body GSM — at most 3 passes. If it does not converge, do NOT force
it: return the last build plus a clarification (plan G2).

Forward mode (no target): render once and report.
"""
from __future__ import annotations
import copy

from .render import render
from .rules_registry import rules


def _within(total, target, tol):
    return total is not None and abs(total - target) / target <= tol


def solve(build_spec: dict, order_spec: dict, env: dict, max_passes: int = 3) -> dict:
    R = rules()
    req = (order_spec.get("req_weight_g") or {}).get("value")
    quoted = (order_spec.get("quoted_weight_g") or {}).get("value")
    target_src = "req_weight_g" if req else ("quoted_weight_g" if quoted else None)
    weight = req or quoted

    if not weight:                                   # FORWARD mode (C2)
        r = render(build_spec, order_spec)
        return {"mode": "forward", "build_spec": build_spec, "physical_bom": r,
                "converged": None, "passes": 0, "history": []}

    target = weight * R.TARGET_FACTOR
    tol = R.TOLERANCE
    b = copy.deepcopy(build_spec)
    gpm_cat, gsm_cat = R.BELT_GPM_CATALOGUE, R.GSM_CATALOGUE
    band = env.get("belt_gpm_band")
    history = []

    for p in range(max_passes):
        r = render(b, order_spec)
        total = r["grand_total_g"]
        history.append({"pass": p, "total_g": total,
                        "belt_gpm": b.get("belt_gpm"),
                        "loop_free_height_cm": b.get("loop_free_height_cm"),
                        "body_gsm": b.get("body_gsm")})
        if total is None:
            break
        if _within(total, target, tol):
            return {"mode": "backward", "build_spec": b, "physical_bom": r,
                    "converged": True, "passes": p + 1, "history": history,
                    "target_g": round(target, 1), "target_from": target_src}
        over = total > target
        moved = False
        # knob 1 — belt gramage, within the load band
        g = b.get("belt_gpm")
        if g in gpm_cat:
            i = gpm_cat.index(g) + (-1 if over else 1)
            if 0 <= i < len(gpm_cat) and (not band or band[0] <= gpm_cat[i] <= band[1]):
                b["belt_gpm"] = gpm_cat[i]
                moved = True
        # knob 2 — loop cut via free height (22..122)
        if not moved:
            fh = b.get("loop_free_height_cm") or R.LOOP["default_free_height_cm"]
            nfh = fh + (-5 if over else 5)
            if 22 <= nfh <= 122:
                b["loop_free_height_cm"] = nfh
                moved = True
        # knob 3 — body GSM, never below the chart floor unless customer stated it
        if not moved:
            gs = b.get("body_gsm")
            if gs in gsm_cat:
                i = gsm_cat.index(gs) + (-1 if over else 1)
                floor = env.get("gsm_floor")
                stated = (order_spec.get("stated_body_gsm") or {}).get("value")
                if 0 <= i < len(gsm_cat) and (stated or not floor or gsm_cat[i] >= floor):
                    b["body_gsm"] = gsm_cat[i]
                    moved = True
        if not moved:
            break

    r = render(b, order_spec)
    clar = {
        "code": "TARGET_WEIGHT_UNREACHABLE" if r["grand_total_g"] else "NOT_RENDERABLE",
        "field": "req_weight_g",
        "question": (
            f"A finished weight near {target:.0f} g "
            f"(= {weight:.0f} - 1%) was not reached within ±2% after "
            f"{len(history)} passes; the build now weighs "
            f"{r['grand_total_g']:.0f} g. Proceed against the bag weight, or "
            f"against the specified GSM?" if r["grand_total_g"] else
            f"This family has no geometry in the renderer yet, so weight cannot "
            f"be solved. (plan §12 O-item)"),
        "achievable_g": r["grand_total_g"],
        "requested_g": weight,
    }
    return {"mode": "backward", "build_spec": b, "physical_bom": r,
            "converged": False, "passes": len(history), "history": history,
            "target_g": round(target, 1), "target_from": target_src,
            "clarification": clar}
