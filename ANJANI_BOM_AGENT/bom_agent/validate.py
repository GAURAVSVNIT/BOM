"""Stage 8 — the validation gate (plan §7). A working subset of the 21 checks;
each recomputes from the rule book, never trusts the model. Severities follow
the plan: C6 makes several of these warnings, not rejects.
"""
from __future__ import annotations

from .rules_registry import rules


def _lines_by_name(pbom):
    out = {}
    for ln in pbom.get("components", []):
        out.setdefault(ln["name"], []).append(ln)
    return out


def validate(build_spec: dict, order_spec: dict, pbom: dict, env: dict) -> dict:
    R = rules()
    findings = []

    def add(check, severity, msg):
        findings.append({"check": check, "severity": severity, "message": msg})

    fam = build_spec.get("family")
    by = _lines_by_name(pbom)

    # V01/V02 — arithmetic + grand total
    if pbom.get("grand_total_g") is not None:
        recomputed = round(sum((l.get("weight_g") or 0) for l in pbom["components"]), 3)
        if abs(recomputed - pbom["grand_total_g"]) > 0.5:
            add("V02_grand_total", "reject",
                f"sum of lines {recomputed} != grand_total {pbom['grand_total_g']}")

    # V03 — mandatory component set
    need = set(env.get("mandatory_components", []))
    have = set(by)
    if need - have:
        add("V03_mandatory_set", "reject",
            f"{fam} is missing {sorted(need - have)}")

    # V04/V05/V06 — phantom / forbidden components
    for bad in env.get("forbidden_components", []):
        if bad in by:
            add("V05_forbidden_component", "reject",
                f"{fam} must not carry {bad}")
    if fam == "u_panel" and len(by.get("SIDE PANEL", [])) not in (0,) and \
            sum(l.get("pieces", 0) for l in by.get("SIDE PANEL", [])) != 2 * (
            2 if build_spec.get("double_layer") else 1):
        add("V06_side_panels", "warn", "u_panel side-panel count is not 2 (or 4 double-layer)")

    # V07 — a tie exists wherever an FS/DS/Skirt exists
    has_spout = any(build_spec.get(k) for k in ("fs_dia_cm", "ds_dia_cm")) or \
        build_spec.get("top_type") == "SKIRT"
    has_tie = any("TIE" in n for n in by)
    if has_spout and not has_tie:
        add("V07_tie_presence", "reject", "FS/DS/Skirt present but no TIE line")

    # V09 — belt capacity (WARNING per plan §13.13: only ~45% of history meets it)
    swl = (order_spec.get("swl_kg") or {}).get("value")
    sf_raw = (order_spec.get("sf") or {}).get("value")
    gpm = build_spec.get("belt_gpm")
    qty = build_spec.get("loop_qty") or 4
    if swl and sf_raw and gpm:
        sfn = float(str(sf_raw).split(":")[0])
        cap = gpm * R.LOOP["kg_per_gram"] * qty
        if cap < swl * sfn:
            add("V09_belt_capacity", "warn",
                f"belt capacity {cap:.0f} kg < SWL×SF {swl*sfn:.0f} kg "
                f"(design target, not a hard limit)")

    # V15 — body GSM is a value the plant actually weaves
    g = build_spec.get("body_gsm")
    if g and g not in R.GSM_CATALOGUE:
        add("V15_gsm_catalogue", "reject", f"body_gsm {g} is off the catalogue")

    # V16/V17 — GSM vs chart floor
    floor = env.get("gsm_floor")
    stated = (order_spec.get("stated_body_gsm") or {}).get("value")
    if floor and g and g < floor:
        if stated:
            add("V17_gsm_below_chart_customer", "warn",
                f"body_gsm {g} < floor {floor}; customer-stated, honoured (C6) — clarify")
        else:
            add("V16_gsm_below_chart", "reject",
                f"body_gsm {g} < floor {floor} and the customer did not state it")

    # V18 — weight vs target
    req = (order_spec.get("req_weight_g") or {}).get("value") or \
        (order_spec.get("quoted_weight_g") or {}).get("value")
    tot = pbom.get("grand_total_g")
    if req and tot:
        target = req * R.TARGET_FACTOR
        if abs(tot - target) / target > R.TOLERANCE:
            add("V18_weight_vs_target", "warn",
                f"{tot:.0f} g is {100*(tot-target)/target:+.1f}% from target {target:.0f} g")

    sev = {"reject": 0, "warn": 0, "advisory": 0}
    for f in findings:
        sev[f["severity"]] = sev.get(f["severity"], 0) + 1
    return {"findings": findings, "counts": sev,
            "ok": sev["reject"] == 0, "n_checks_run": 10}
