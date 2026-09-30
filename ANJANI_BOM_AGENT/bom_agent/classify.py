"""Stage 2 — deterministic classification + SWL derivation (plan §1.2, §2).

Family / loop / top by fixed rule — never a model judgement. SWL from bulk
density × fill volume when the customer gave a product + volume instead of a load
(plan G6); the density table (bulk_density.json) is not digitised yet, so that
path currently raises a clarification instead.
"""
from __future__ import annotations

from .contracts import OrderSpec
from .rules_registry import rules


def classify(o: OrderSpec) -> dict:
    R = rules()
    raw = " ".join(str(o.val(k) or "") for k in
                   ("stated_bag_type_raw", "loop_colour")) + " " + (o.raw_text or "")
    belt = o.val("belt_width_mm")

    fam, fam_src = R.classify_family(raw, belt)
    loop, loop_src = R.classify_loop_type(raw, belt)

    # TOP (plan §1.2)
    tt = o.val("top_type")
    if tt:
        top = tt
    elif o.val("fs_dia_cm"):
        top = "FS_SPOUT"
    else:
        top = "OPEN_TOP"                       # nothing stated -> open top [E, E6]
    top_src = "stated" if tt else "house_default"

    bt = o.val("bottom_type")
    bottom = bt or ("DS_SPOUT" if o.val("ds_dia_cm") else "FLAT_BOTTOM")

    return {
        "family": fam, "loop_type": loop, "top_type": top, "bottom_type": bottom,
        "_provenance": {"family": fam_src, "loop_type": loop_src, "top_type": top_src},
    }


def derive_swl(o: OrderSpec) -> tuple[float | None, str | None]:
    """Returns (swl_kg, note). Real density lookup is Phase 3 (plan §8)."""
    if o.provided("swl_kg"):
        return o.val("swl_kg"), None
    return None, ("SWL not stated and bulk-density lookup is not yet available "
                  "(needs bulk_density.json — plan §12 O-item). Ask the customer.")
