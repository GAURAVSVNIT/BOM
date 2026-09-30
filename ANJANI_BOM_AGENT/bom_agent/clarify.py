"""Stage 9a — the clarification list (plan §4.4). A co-equal output, not an error
path: for every OrderSpec gap the rule book cares about, emit the question to put
to the customer; record every assumption the pipeline made.
"""
from __future__ import annotations

from .contracts import OrderSpec, ClarificationItem, ClarificationList

QUESTION = {
    "swl_kg": ("SWL_MISSING", "Safe working load is not stated. Confirm the SWL, "
               "or give the product and fill volume so we can compute it."),
    "sf": ("SF_MISSING", "Safety factor is not stated. Single-trip (5:1) or multi-trip (6:1)?"),
    "ext_L_cm": ("SIZE_MISSING", "Bag size is not stated. Confirm L × W × H in cm."),
    "req_weight_g": ("TARGET_WEIGHT_MISSING", "No required bag weight given. We will "
                     "build to the load chart and report the resulting weight — confirm that is acceptable."),
    "stated_bag_type_raw": ("CONSTRUCTION_NOT_STATED", "Construction not stated. We have "
                            "assumed U+2 panel with corner loop, our house default. Confirm."),
    "loop_LL_cm": ("LOOP_LENGTH_ASSUMED", "Loop attachment lengths not stated. We assumed "
                   "LL 65% / SL 35% of bag height with 25 cm free height. Confirm."),
    "product_contents": ("PRODUCT_NOT_STATED",
                         "What product will the bag carry? It determines the fabric GSM."),
    "has_liner": ("LINER_NOT_STATED", "No liner specified — we will not fit one. Confirm."),
    "static_type": ("STATIC_TYPE_NOT_STATED", "Static protection type not stated. Type A "
                    "assumed (non-flammable contents only)."),
}
BLOCKING = {"swl_kg", "ext_L_cm"}


def build_clarification(o: OrderSpec, cls: dict, build_spec: dict, env: dict,
                        extra_flags: list[str] | None = None) -> ClarificationList:
    cl = ClarificationList()
    for field, (code, q) in QUESTION.items():
        if o.get(field).state == "not_specified":
            item = ClarificationItem(code=code, field=field, question=q)
            (cl.blocking if field in BLOCKING else cl.advisory).append(item)

    if o.get("stated_bag_type_raw").state == "not_specified":
        cl.assumptions_made.append({"field": "family", "value": cls["family"],
                                    "reason": "not stated; house default"})
    if o.get("top_type").state == "not_specified":
        cl.assumptions_made.append({"field": "top_type", "value": cls["top_type"],
                                    "reason": "not stated; OPEN_TOP default"})
    if o.get("has_liner").state == "not_specified":
        cl.assumptions_made.append({"field": "has_liner", "value": False,
                                    "reason": "never added silently"})

    floor = env.get("gsm_floor")
    g = build_spec.get("body_gsm")
    if floor and g and g < floor:
        cl.advisory.append(ClarificationItem(
            code="GSM_BELOW_CHART", field="body_gsm",
            question=(f"Body GSM {g} is below our {floor} GSM standard for this "
                      f"load. Proceed against the bag weight, or against the specified GSM?"),
            why="C6 — customer-stated GSM is honoured, but the trade must be explicit.",
            extra={"chart_floor": floor, "chosen": g}))

    for msg in (extra_flags or []):
        cl.advisory.append(ClarificationItem(code="PIPELINE_NOTE", field="-",
                                             question=msg))
    return cl
