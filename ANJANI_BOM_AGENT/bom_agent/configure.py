"""Stage 5 — configuration (adapter B).  OrderSpec + retrieved + envelope -> BuildSpec.

With a model `client`: grammar-constrained call; the output is shape-checked and
any GSM below the envelope floor is kept (plan C6) but flagged. Without a client:
a deterministic configurer that starts from the nearest retrieved neighbour and
overlays the customer's stated values and the envelope — the plan's "no-model
fallback configurer" (§3, configure/deterministic.py).
"""
from __future__ import annotations
import json

from .contracts import OrderSpec, BuildSpec

SYSTEM_B = (
    "You are a senior FIBC bag design engineer at Anjani Interweave. You are "
    "given what the customer asked for, the three nearest bags the plant has "
    "actually built, and the rule envelope for this load. Decide every "
    "parameter needed to build the bag and return a BuildSpec JSON. You choose "
    "from closed vocabularies only: never output a width, a cut length, a weight "
    "or a price — those are computed downstream from your decisions. If the "
    "customer stated a GSM below the chart floor, honour it and flag it. "
    "Output JSON only."
)


def _user_prompt(order_spec, retrieved, env) -> str:
    j = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"))
    return (f"ORDER_SPEC:\n{j(order_spec)}\n\n"
            f"RETRIEVED_NEIGHBOURS:\n{j(retrieved)}\n\n"
            f"RULE_ENVELOPE:\n{j(env)}")


def _deterministic(order_spec, cls, retrieved, env) -> dict:
    base = dict(retrieved[0]["build_spec"]) if retrieved else {}
    b = dict(base)
    b.update({
        "family": cls["family"], "loop_type": cls["loop_type"],
        "top_type": cls["top_type"], "bottom_type": cls["bottom_type"],
    })
    # overlay stated customer values
    for src, dst in (("fs_dia_cm", "fs_dia_cm"), ("fs_height_cm", "fs_height_cm"),
                     ("ds_dia_cm", "ds_dia_cm"), ("ds_height_cm", "ds_height_cm"),
                     ("fs_closure", "fs_closure"), ("ds_closure", "ds_closure"),
                     ("belt_width_mm", "belt_width_mm"), ("loop_qty", "loop_qty"),
                     ("loop_free_height_cm", "loop_free_height_cm"),
                     ("loop_LL_cm", "loop_attach_long_cm"),
                     ("loop_SL_cm", "loop_attach_short_cm"),
                     ("fabric_colour", "fabric_colour")):
        f = order_spec.get(src) or {}
        if f.get("state") == "provided" and f.get("value") is not None:
            b[dst] = f.get("value")
    # GSM: stated -> honour (plan C6); else neighbour, but never start below the
    # chart floor when the customer did not state one (the solver may only go
    # below the floor on an explicit C6 override).
    stated = (order_spec.get("stated_body_gsm") or {}).get("value")
    floor = env.get("gsm_floor")
    if stated:
        b["body_gsm"] = stated
    else:
        cur = b.get("body_gsm")
        if not cur or (floor and cur < floor):
            b["body_gsm"] = floor or cur
    if not b.get("belt_gpm") and env.get("belt_gpm_band"):
        b["belt_gpm"] = env["belt_gpm_band"][0]
    b.pop("_provenance", None)
    b.setdefault("has_label", True)
    return b


def configure(order_spec: dict, cls: dict, retrieved: list, env: dict,
              client=None) -> tuple[BuildSpec, list]:
    flags = []
    if client is not None:
        raw = client.complete("b", SYSTEM_B, _user_prompt(order_spec, retrieved, env))
        try:
            d = json.loads(raw)
        except json.JSONDecodeError:
            flags.append("adapter_b returned non-JSON; used deterministic fallback")
            d = _deterministic(order_spec, cls, retrieved, env)
    else:
        d = _deterministic(order_spec, cls, retrieved, env)

    bs = BuildSpec.from_dict(d)
    # keep the deterministic classification authoritative
    for k in ("family", "loop_type"):
        if bs.get(k) != cls[k]:
            flags.append(f"model {k}={bs.get(k)} overridden by rule -> {cls[k]}")
            bs.set(k, cls[k])
    floor = env.get("gsm_floor")
    if floor and bs.get("body_gsm") and bs.get("body_gsm") < floor:
        flags.append(f"body_gsm {bs.get('body_gsm')} below chart floor {floor} "
                     f"(honoured per C6 — raise GSM_BELOW_CHART clarification)")
    return bs, flags
