from __future__ import annotations

from collections import Counter
from typing import Any

from app.contracts.models import PhysicalBOM, ValidationDecision, ValidationIssue, ValidationReport
from app.rules.loader import RuleBook, load_rulebook
from app.rules.u_panel_engine import fabric_weight, linear_weight


def _issue(code: str, path: str, message: str, actual: Any = None, allowed: list[Any] | None = None, reference: Any = None) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        path=path,
        message=message,
        allowed_values=allowed,
        actual_value=actual,
        reference_value=reference,
    )


def _minimum_body_gsm(bom: PhysicalBOM, rules: RuleBook) -> int:
    family = "square_corner" if bom.bag_type in {"u_panel", "four_panel", "four_panel_baffle", "two_panel"} else "cross_corner"
    sf_key = 6 if bom.sf >= 6 else 5
    for row in rules.hard["minimum_structural_gsm_rules"]:
        if row["bag_family"] == family and row["sf"] == sf_key and row["swl_min"] <= bom.swl_kg <= row["swl_max"]:
            return int(row["body_gsm_min"])
    return 240


def validate_bom(bom: PhysicalBOM, rules: RuleBook | None = None, generated: bool = True) -> ValidationReport:
    rules = rules or load_rulebook()
    hard: list[ValidationIssue] = []
    soft: list[ValidationIssue] = []

    allowed_components = set(rules.hard["canonical_components"])
    allowed_lami = set(rules.hard["lamination_values"])
    approved_widths = {float(w) for w in rules.hard["approved_loom_widths_cm"]}
    allowed_gsm = {float(v) for v in rules.hard["allowed_fabric_gsm_values"]}
    allowed_gpm = {float(v) for v in rules.hard["allowed_linear_gpm_values"]}
    policy = rules.hard["component_policy"]

    names = [c.canonical_name for c in bom.components]
    name_set = set(names)
    required = set(rules.hard["mandatory_by_bag_type"].get(bom.bag_type, []))
    missing = sorted(required - name_set)
    for name in missing:
        hard.append(_issue("MISSING_MANDATORY_COMPONENT", "components", f"{name} is mandatory for {bom.bag_type}.", name))

    counts = Counter(names)
    for name, count in counts.items():
        duplicate_rule = policy.get(name, {}).get("duplicates", "forbidden")
        if count > 1 and duplicate_rule == "forbidden":
            hard.append(_issue("FORBIDDEN_DUPLICATE_COMPONENT", "components", f"{name} appears {count} times but duplicates are forbidden.", count))

    body_min = _minimum_body_gsm(bom, rules)
    for idx, comp in enumerate(bom.components):
        path = f"components[{idx}]"
        if comp.canonical_name not in allowed_components:
            hard.append(_issue("FORBIDDEN_COMPONENT", f"{path}.canonical_name", "Component name is not canonical.", comp.canonical_name, sorted(allowed_components)))
            continue

        comp_policy = policy.get(comp.canonical_name, {})
        for field in comp_policy.get("required", []):
            if getattr(comp, field) is None:
                allowed_nulls = set(comp_policy.get("allowed_nulls", []))
                if field not in allowed_nulls:
                    hard.append(_issue("MISSING_COMPONENT_FIELD", f"{path}.{field}", f"{field} is required for {comp.canonical_name}."))

        if comp.lami_ul not in allowed_lami:
            hard.append(_issue("INVALID_LAMINATION", f"{path}.lami_ul", "Invalid lamination value.", comp.lami_ul, sorted(v for v in allowed_lami if v is not None)))

        comp_type = comp_policy.get("type")
        if comp.gsm_area is not None:
            if comp_type == "fabric_area" and float(comp.gsm_area) not in allowed_gsm:
                hard.append(_issue("UNAPPROVED_GSM", f"{path}.gsm_area", "Fabric GSM is not in allowed observed table.", comp.gsm_area))
            if comp_type == "fabric_area" and comp.width_cm is not None and float(comp.width_cm) not in approved_widths:
                hard.append(_issue("FORBIDDEN_LOOM_WIDTH", f"{path}.width_cm", "Fabric width is not in approved loom table.", comp.width_cm))
            if comp.canonical_name in {"BODY PANEL", "SIDE PANEL", "BOTTOM PANEL"} and comp.gsm_area < body_min:
                hard.append(_issue("GSM_BELOW_STRUCTURAL_MINIMUM", f"{path}.gsm_area", "Structural GSM is below load threshold.", comp.gsm_area, reference=body_min))
            if comp_type == "fabric_area" and comp.width_cm is not None and comp.cut_cm is not None:
                expected = fabric_weight(comp.gsm_area, comp.width_cm, comp.cut_cm, comp.qty)
                if abs(expected - comp.weight_g) > rules.hard["weight_formula_tolerance_g"]["generated" if generated else "historical"]:
                    hard.append(_issue("FABRIC_WEIGHT_FORMULA_MISMATCH", f"{path}.weight_g", "Fabric weight does not match formula.", comp.weight_g, reference=expected))

        if comp.gsm_per_m is not None:
            if float(comp.gsm_per_m) not in allowed_gpm:
                hard.append(_issue("UNAPPROVED_GPM", f"{path}.gsm_per_m", "Linear GPM is not in allowed observed table.", comp.gsm_per_m))
            if comp_type == "linear" and comp.cut_cm is not None:
                expected = linear_weight(comp.gsm_per_m, comp.cut_cm, comp.qty)
                if abs(expected - comp.weight_g) > rules.hard["weight_formula_tolerance_g"]["generated" if generated else "historical"]:
                    hard.append(_issue("LINEAR_WEIGHT_FORMULA_MISMATCH", f"{path}.weight_g", "Linear weight does not match formula.", comp.weight_g, reference=expected))

    total = round(sum(c.weight_g for c in bom.components), 3)
    if generated and abs(total - bom.computed_total_g) > rules.hard["weight_formula_tolerance_g"]["generated"]:
        hard.append(_issue("COMPUTED_TOTAL_MISMATCH", "computed_total_g", "Computed total does not equal component sum.", bom.computed_total_g, reference=total))
    if generated and abs(bom.bag_weight_actual_g - bom.computed_total_g) > rules.hard["weight_formula_tolerance_g"]["generated"]:
        hard.append(_issue("ACTUAL_TOTAL_MISMATCH", "bag_weight_actual_g", "Generated actual must equal computed total.", bom.bag_weight_actual_g, reference=bom.computed_total_g))

    if bom.bag_weight_target_g:
        gap_pct = abs(bom.bag_weight_actual_g - bom.bag_weight_target_g) / bom.bag_weight_target_g * 100
        if gap_pct > rules.heuristics["target_actual_weight_warning_pct"]:
            soft.append(_issue("TARGET_ACTUAL_WEIGHT_GAP", "bag_weight_target_g", "Target and actual differ by more than warning threshold.", round(gap_pct, 2), reference=bom.bag_weight_target_g))
        elif gap_pct > 0:
            soft.append(_issue("TARGET_ACTUAL_WEIGHT_GAP_MINOR", "bag_weight_actual_g", "Generated actual differs from target within tolerance.", bom.bag_weight_actual_g, reference=bom.bag_weight_target_g))

    decision = ValidationDecision.RETRY if hard else (ValidationDecision.PASS_WITH_WARNINGS if soft else ValidationDecision.PASS)
    return ValidationReport(
        schema_pass=True,
        hard_failures=hard,
        soft_warnings=soft,
        retriable=bool(hard),
        error_context_for_llm={
            "fix_only_these_paths": [h.path for h in hard],
            "do_not_change_paths": ["bag_type", "swl_kg", "sf", "int_L", "int_W", "int_H"],
        } if hard else {},
        final_decision=decision,
    )
