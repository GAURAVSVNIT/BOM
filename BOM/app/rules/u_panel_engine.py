from __future__ import annotations

from uuid import uuid4

from app.contracts.models import (
    Assumption,
    BOMComponent,
    FieldStatus,
    PhysicalBOM,
    RuleHit,
    StructuredSpec,
)
from app.rules.loader import RuleBook, load_rulebook, nearest_approved_width
from app.rules.gsm_model import predict_u_panel_body_gsm


class InsufficientSpecError(ValueError):
    pass


def _num(field, name: str) -> float:
    if field.value is None or field.status == FieldStatus.MISSING:
        raise InsufficientSpecError(f"Missing required field: {name}")
    return float(field.value)


def _bool_value(field, default: bool = False) -> bool:
    return bool(field.value) if field.value is not None else default


def fabric_weight(gsm_area: float, width_cm: float, cut_cm: float, qty: float = 1) -> float:
    return round(gsm_area * width_cm * cut_cm * qty / 10000, 3)


def linear_weight(gsm_per_m: float, cut_cm: float, qty: float = 1) -> float:
    return round(gsm_per_m * cut_cm * qty / 100, 3)


def _minimum_body_gsm(swl: float, sf: float, rules: RuleBook) -> int:
    bag_family = "square_corner"
    sf_key = 6 if sf >= 6 else 5
    for row in rules.hard["minimum_structural_gsm_rules"]:
        if row["bag_family"] == bag_family and row["sf"] == sf_key and row["swl_min"] <= swl <= row["swl_max"]:
            return int(row["body_gsm_min"])
    return 240


def _select_body_gsm(
    swl: float,
    sf: float,
    body_laminated: bool,
    rules: RuleBook,
    ext_L: float,
    ext_W: float,
    ext_H: float,
    int_L: float,
    int_W: float,
    int_H: float,
    has_printing: bool,
    has_liner: bool,
    has_ds_spout: bool,
    has_fs_spout: bool,
    has_ddp: bool,
    has_doc: bool,
    loop_width_mm: float | None,
) -> int:
    minimum = _minimum_body_gsm(swl, sf, rules)
    ml_gsm = predict_u_panel_body_gsm(
        swl,
        sf,
        ext_L,
        ext_W,
        ext_H,
        int_L,
        int_W,
        int_H,
        has_printing,
        has_liner,
        has_ds_spout,
        has_fs_spout,
        has_ddp,
        has_doc,
        loop_width_mm,
        rules.hard["allowed_fabric_gsm_values"],
        minimum,
    )
    if ml_gsm is not None:
        return max(minimum, ml_gsm)
    design_load = str(int(swl * sf))
    candidates = rules.heuristics.get("u_panel_body_gsm_modes", {}).get(design_load, [])
    legal = [int(v) for v in candidates if int(v) >= minimum]
    if legal:
        return min(legal)
    if body_laminated and minimum < 90:
        return 90
    return minimum


def _loop_defaults(swl: float, sf: float, rules: RuleBook) -> tuple[float, float]:
    sf_key = 6 if sf >= 6 else 5
    for row in rules.defaults["loop_standard_table"]:
        if row["loop_family"] == "corner_loop" and row["sf"] == sf_key and row["swl_min"] <= swl <= row["swl_max"]:
            return float(row["gsm_per_m"]), float(row["width_mm"])
    return 50.0, 50.0


def _component(
    sr: int,
    name: str,
    weight: float,
    gsm_area: float | None = None,
    gsm_per_m: float | None = None,
    lami_ul: str | None = None,
    color: str | None = None,
    width_cm: float | None = None,
    cut_cm: float | None = None,
    qty: float = 1,
    remark: str | None = None,
) -> BOMComponent:
    return BOMComponent(
        sr=sr,
        canonical_name=name,
        gsm_area=gsm_area,
        gsm_per_m=gsm_per_m,
        lami_ul=lami_ul,
        color=color,
        width_cm=width_cm,
        cut_cm=cut_cm,
        qty=qty,
        weight_g=weight,
        remark=remark,
        source="rule_engine",
    )


def _required_optional(spec: StructuredSpec) -> set[str]:
    required: set[str] = set()
    if spec.top_type.value == "TOP_PANEL":
        required.add("TOP PANEL")
    elif spec.top_type.value in {"SKIRT", "DUFFLE"}:
        required.add("SKIRT")
    elif spec.top_type.value == "TOP_FLAP":
        required.add("TOP FLAP")

    if _bool_value(spec.accessories.has_fs_spout):
        required.update(["FILLING SPOUT", "FS TIE"])
    if _bool_value(spec.accessories.has_ds_spout) or spec.bottom_type.value in {"DISCHARGE_SPOUT", "IRIS", "PETAL"}:
        required.update(["DISCHARGE SPOUT", "DS TIE"])
    if spec.accessories.ds_closure.value == "IRIS" or spec.bottom_type.value == "IRIS":
        required.add("DS TIE")
    if spec.accessories.ds_closure.value == "PETAL" or spec.bottom_type.value == "PETAL":
        required.add("PETAL TIE")
    if _bool_value(spec.accessories.has_liner):
        required.add("LINER")
    if _bool_value(spec.accessories.has_doc_pocket):
        required.add("DOC POCKET")
    if _bool_value(spec.accessories.has_ddp):
        required.add("DDP")
    if _bool_value(spec.accessories.has_stevedore):
        required.add("STEVEDORE LOOP")
    return required


def generate_u_panel_bom(spec: StructuredSpec, rules: RuleBook | None = None) -> PhysicalBOM:
    rules = rules or load_rulebook()
    if spec.bag_type.value != "u_panel":
        raise InsufficientSpecError("U-panel engine received non-u_panel spec")

    ext_L = _num(spec.dimensions.ext_L, "ext_L")
    ext_W = _num(spec.dimensions.ext_W, "ext_W")
    ext_H = _num(spec.dimensions.ext_H, "ext_H")
    int_L = _num(spec.dimensions.int_L, "int_L")
    int_W = _num(spec.dimensions.int_W, "int_W")
    int_H = _num(spec.dimensions.int_H, "int_H")
    swl = _num(spec.swl_kg, "swl_kg")
    sf = _num(spec.sf, "sf")
    body_laminated = _bool_value(spec.body_laminated, False)
    color = spec.fabric_color.value or "WHITE"
    widths = rules.hard["approved_loom_widths_cm"]
    defaults = rules.defaults["u_panel_defaults"]

    has_printing = bool(spec.printing.printing_sides.value or spec.printing.printing_colors.value)
    body_gsm = _select_body_gsm(
        swl,
        sf,
        body_laminated,
        rules,
        ext_L,
        ext_W,
        ext_H,
        int_L,
        int_W,
        int_H,
        has_printing,
        _bool_value(spec.accessories.has_liner),
        _bool_value(spec.accessories.has_ds_spout),
        _bool_value(spec.accessories.has_fs_spout),
        _bool_value(spec.accessories.has_ddp),
        _bool_value(spec.accessories.has_doc_pocket),
        float(spec.loop.loop_width_mm.value) if spec.loop.loop_width_mm.value is not None else None,
    )
    body_lami = "LAMINATED" if body_laminated else "UNLAMINATED"
    top_gsm = float(defaults["top_panel_gsm_area"])
    spout_gsm = float(defaults["spout_gsm_area"])
    tie_gpm = float(defaults["tie_gsm_per_m"])
    loop_gpm_default, loop_width_mm_default = _loop_defaults(swl, sf, rules)
    loop_gpm = loop_gpm_default
    loop_width_cm = float(spec.loop.loop_width_mm.value or loop_width_mm_default) / 10
    loop_ll = float(spec.loop.loop_LL_cm.value or defaults["loop_LL_cm"])
    loop_sl = float(spec.loop.loop_SL_cm.value or defaults["loop_SL_cm"])
    loop_qty = float(spec.loop.loop_qty.value or defaults["loop_qty"])

    components: list[BOMComponent] = []
    sr = 1

    body_width = nearest_approved_width(ext_W + 8, widths)
    body_cut = 2 * ext_H + ext_L + 10
    components.append(_component(sr, "BODY PANEL", fabric_weight(body_gsm, body_width, body_cut), body_gsm, None, body_lami, color, body_width, body_cut, 1, "width=ext_W+8; cut=2*ext_H+ext_L+10"))
    sr += 1

    side_width = nearest_approved_width(ext_W + 8, widths)
    side_cut = ext_H + 8
    components.append(_component(sr, "SIDE PANEL", fabric_weight(body_gsm, side_width, side_cut, 2), body_gsm, None, body_lami, color, side_width, side_cut, 2, "qty=2; width=ext_W+8; cut=ext_H+8"))
    sr += 1

    required = _required_optional(spec)
    if "TOP PANEL" in required:
        top_width = nearest_approved_width(ext_L + 8, widths)
        top_cut = nearest_approved_width(ext_W + 8, widths)
        components.append(_component(sr, "TOP PANEL", fabric_weight(top_gsm, top_width, top_cut), top_gsm, None, "LAMINATED", color, top_width, top_cut, 1, "default top panel"))
        sr += 1
    if "SKIRT" in required:
        skirt_h = 80.0
        if spec.top_type.source_text:
            import re
            m = re.search(r"(\d+(?:\.\d+)?)", spec.top_type.source_text)
            if m:
                skirt_h = float(m.group(1))
        skirt_width = nearest_approved_width(skirt_h + 5, widths)
        skirt_cut = 2 * (ext_L + ext_W) + 12
        components.append(_component(sr, "SKIRT", fabric_weight(top_gsm, skirt_width, skirt_cut), top_gsm, None, "LAMINATED", color, skirt_width, skirt_cut, 1, "perimeter+12"))
        sr += 1

    fs_cut = None
    if "FILLING SPOUT" in required:
        fs_dia = float(spec.accessories.fs_spout_dia_cm.value or 40)
        fs_h = float(spec.accessories.fs_spout_h_cm.value or 50)
        fs_width = nearest_approved_width(fs_h + 5, widths)
        fs_cut = round(fs_dia * 3.14 + 12, 1)
        components.append(_component(sr, "FILLING SPOUT", fabric_weight(spout_gsm, fs_width, fs_cut), spout_gsm, None, "LAMINATED", color, fs_width, fs_cut, 1, "cut=dia*3.14+12"))
        sr += 1
        components.append(_component(sr, "FS TIE", linear_weight(tie_gpm, 125), None, tie_gpm, "PP", color, 1.5, 125, 1, "standard FS tie"))
        sr += 1

    ds_cut = None
    if "DISCHARGE SPOUT" in required:
        ds_dia = float(spec.accessories.ds_spout_dia_cm.value or 35)
        ds_h = float(spec.accessories.ds_spout_h_cm.value or 50)
        closure = spec.accessories.ds_closure.value or spec.bottom_type.value
        raw_width = ds_h + 5 + (ds_dia / 2) + 7 if closure == "IRIS" else ds_h + 5
        ds_width = nearest_approved_width(raw_width, widths)
        ds_cut = round(ds_dia * 3.14 + 12, 1)
        components.append(_component(sr, "DISCHARGE SPOUT", fabric_weight(spout_gsm, ds_width, ds_cut), spout_gsm, None, "LAMINATED", color, ds_width, ds_cut, 1, "cut=dia*3.14+12"))
        sr += 1
        if closure == "IRIS":
            iris_cut = round(ds_dia * 3.14 + 38, 1)
            components.append(_component(sr, "DS TIE", linear_weight(tie_gpm, iris_cut), None, tie_gpm, "PP", color, 1.5, iris_cut, 1, "iris tie"))
            sr += 1
        components.append(_component(sr, "DS TIE", linear_weight(tie_gpm, 125), None, tie_gpm, "PP", color, 1.5, 125, 1, "standard DS tie"))
        sr += 1

    loop_cut = loop_ll + loop_sl + 50
    components.append(_component(sr, "CORNER LOOP", linear_weight(loop_gpm, loop_cut, loop_qty), None, loop_gpm, "PP", spec.loop.loop_color.value or color, loop_width_cm, loop_cut, loop_qty, "LL+SL+50"))
    sr += 1

    if "LINER" in required:
        micron = float(spec.accessories.liner_micron.value or rules.defaults["liner_defaults"]["micron"])
        liner_width = int_W + rules.defaults["liner_defaults"]["width_add_cm"]
        liner_cut = 2 * int_H + int_L + rules.defaults["liner_defaults"]["cut_add_cm"]
        liner_gsm = round(micron * 1.84, 3)
        components.append(_component(sr, "LINER", fabric_weight(liner_gsm, liner_width, liner_cut), liner_gsm, None, "LDPE", "NATURAL", liner_width, liner_cut, 1, f"{micron} micron"))
        sr += 1

    if "DOC POCKET" in required:
        size = spec.accessories.doc_pocket_size.value or "A4"
        doc_rule = rules.defaults["doc_pocket_sizes"].get(size, rules.defaults["doc_pocket_sizes"]["A4"])
        components.append(_component(sr, "DOC POCKET", fabric_weight(doc_rule["gsm_area"], doc_rule["width_cm"], doc_rule["cut_cm"]), doc_rule["gsm_area"], None, doc_rule["lami_ul"], "NATURAL", doc_rule["width_cm"], doc_rule["cut_cm"], 1, size))
        sr += 1

    if "DDP" in required:
        ddp_gpm = float(rules.heuristics["ddp_path_heuristic"]["gsm_per_m"])
        path = 2 * body_cut + 4 * ext_L + (fs_cut or 0) + (ds_cut or 0) + 50
        components.append(_component(sr, "DDP", linear_weight(ddp_gpm, path), None, ddp_gpm, "PP", "WHITE", 0.75, path, 1, "estimated path length"))
        sr += 1

    stitching = float(rules.heuristics["stitching_weight_heuristic"]["fallback_weight_g"])
    components.append(_component(sr, "STITCHING", stitching, None, None, None, color, None, None, 1, "fixed heuristic"))
    sr += 1
    components.append(_component(sr, "LABEL", float(defaults["label_weight_g"]), None, None, None, None, None, None, 1, "mandatory"))

    total = round(sum(c.weight_g for c in components), 3)
    target = spec.bag_weight_target_g.value if spec.bag_weight_target_g.value is not None else None
    assumptions = [
        Assumption(id="A001", field="body_gsm", assumption=f"Selected {body_gsm} GSM with structural minimum floor and U-panel data model advisory.", basis="minimum_structural_plus_ml_advisory"),
        Assumption(id="A002", field="approved_widths", assumption="Widths snapped upward to approved loom table.", basis="width_rounding_policy"),
    ]
    rule_hits = [
        RuleHit(rule_id="U_PANEL_MANDATORY_BY_BAG_TYPE", rule_level="hard_constraint"),
        RuleHit(rule_id="U_PANEL_COMPONENT_PRESENCE_BY_FLAGS", rule_level="hard_constraint"),
        RuleHit(rule_id="MINIMUM_STRUCTURAL_GSM", rule_level="hard_constraint"),
        RuleHit(rule_id="U_PANEL_GEOMETRY", rule_level="hard_constraint"),
        RuleHit(rule_id="LOOP_STANDARD_TABLE", rule_level="default_preference"),
        RuleHit(rule_id="U_PANEL_GSM_MODEL_ADVISORY", rule_level="fallback_heuristic"),
    ]

    return PhysicalBOM(
        bom_id=f"bom-{uuid4()}",
        source="rule_engine",
        source_spec_id=spec.spec_id,
        customer=spec.customer.value,
        ref_no=spec.ref_no.value,
        bag_type="u_panel",
        swl_kg=swl,
        sf=sf,
        ext_L=ext_L,
        ext_W=ext_W,
        ext_H=ext_H,
        int_L=int_L,
        int_W=int_W,
        int_H=int_H,
        bag_weight_target_g=target,
        bag_weight_actual_g=total,
        computed_total_g=total,
        components=components,
        assumptions=assumptions,
        rule_hits=rule_hits,
        constraint_inputs={
            "design_load_kg": swl * sf,
            "static_rule_table_version": rules.hard["version"],
            "body_gsm_min": _minimum_body_gsm(swl, sf, rules),
            "body_gsm_selected": body_gsm,
        },
    )
