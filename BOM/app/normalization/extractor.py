from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.contracts import CustomerQueryRaw, StructuredSpec
from app.contracts.models import (
    AccessorySpec,
    DimensionsSpec,
    FieldEnvelope,
    FieldStatus,
    LoopSpec,
    PrintingSpec,
)


@dataclass
class NormalizationResult:
    structured_spec: StructuredSpec
    changes: list[dict[str, Any]]


def env(
    value: Any,
    unit: str | None,
    status: FieldStatus,
    confidence: float,
    source_text: str | None = None,
    source: str | None = "customer_text",
) -> FieldEnvelope:
    return FieldEnvelope(
        value=value,
        unit=unit,
        status=status,
        confidence=confidence,
        source_text=source_text,
        source=source if status != FieldStatus.NOT_SPECIFIED else None,
    )


def missing(unit: str | None = None) -> FieldEnvelope:
    return env(None, unit, FieldStatus.MISSING, 0.0, None, None)


def not_specified(unit: str | None = None, value: Any = None) -> FieldEnvelope:
    return env(value, unit, FieldStatus.NOT_SPECIFIED, 1.0, None, None)


def inferred(value: Any, unit: str | None, confidence: float, basis: str) -> FieldEnvelope:
    return FieldEnvelope(
        value=value,
        unit=unit,
        status=FieldStatus.INFERRED,
        confidence=confidence,
        source_text=None,
        source=basis,
    )


def _text(raw: CustomerQueryRaw) -> str:
    attachment_text = " ".join(a.ocr_text or "" for a in raw.attachments)
    return f"{raw.raw_text} {attachment_text}".strip()


def _find_dimensions(text: str) -> tuple[float, float, float, str] | None:
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:x|\*|X|by)\s*(\d+(?:\.\d+)?)\s*(?:x|\*|X|by)\s*(\d+(?:\.\d+)?)\s*(?:cm|cms|centimeter|centimeters)?",
        text,
        re.IGNORECASE,
    )
    if not match:
        compact = re.search(r"\b(\d{2,3})(\d{2,3})(\d{2,3})\b", text)
        if not compact:
            return None
        vals = [float(compact.group(i)) for i in range(1, 4)]
        return vals[0], vals[1], vals[2], compact.group(0)
    return float(match.group(1)), float(match.group(2)), float(match.group(3)), match.group(0)


def _find_number(pattern: str, text: str) -> tuple[float, str] | None:
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return None
    return float(match.group(1)), match.group(0)


def _contains_any(text: str, phrases: list[str]) -> bool:
    low = text.lower()
    return any(p in low for p in phrases)


def _bool_field(text: str, positive: list[str], negative: list[str], default_false: bool = False) -> FieldEnvelope:
    low = text.lower()
    if any(p in low for p in negative):
        return env(False, None, FieldStatus.PROVIDED, 0.9, next(p for p in negative if p in low))
    if any(p in low for p in positive):
        return env(True, None, FieldStatus.PROVIDED, 0.9, next(p for p in positive if p in low))
    if default_false:
        return inferred(False, None, 0.75, "normalization_default_false")
    return not_specified(None, False)


def normalize_customer_query(raw: CustomerQueryRaw) -> NormalizationResult:
    text = _text(raw)
    low = text.lower()
    changes: list[dict[str, Any]] = []

    bag_type = missing()
    if _contains_any(low, ["u+2", "u panel", "u-panel", "u pannel", "u-pannel"]):
        bag_type = env("u_panel", None, FieldStatus.PROVIDED, 0.95, "u_panel alias")
        changes.append({"field": "bag_type", "value": "u_panel", "basis": "alias"})
    elif _contains_any(low, ["circular", "tubular"]):
        bag_type = env("circular", None, FieldStatus.PROVIDED, 0.85, "circular/tubular")
    elif _contains_any(low, ["baffle", "q bag", "anti bulge"]):
        bag_type = env("four_panel_baffle", None, FieldStatus.PROVIDED, 0.85, "baffle")

    dims = _find_dimensions(text)
    int_L = int_W = int_H = missing("cm")
    ext_L = ext_W = ext_H = missing("cm")
    if dims:
        L, W, H, source_text = dims
        if _contains_any(low, ["outer", "external", "od", "outside"]):
            ext_L = env(L, "cm", FieldStatus.PROVIDED, 0.94, source_text)
            ext_W = env(W, "cm", FieldStatus.PROVIDED, 0.94, source_text)
            ext_H = env(H, "cm", FieldStatus.PROVIDED, 0.94, source_text)
            int_L = inferred(max(L - 4, 0), "cm", 0.7, "external_minus_4cm_default")
            int_W = inferred(max(W - 4, 0), "cm", 0.7, "external_minus_4cm_default")
            int_H = inferred(max(H - 4, 0), "cm", 0.7, "external_minus_4cm_default")
        else:
            int_L = env(L, "cm", FieldStatus.PROVIDED, 0.96, source_text)
            int_W = env(W, "cm", FieldStatus.PROVIDED, 0.96, source_text)
            int_H = env(H, "cm", FieldStatus.PROVIDED, 0.96, source_text)
            ext_L = inferred(L + 4, "cm", 0.7, "internal_plus_4cm_default")
            ext_W = inferred(W + 4, "cm", 0.7, "internal_plus_4cm_default")
            ext_H = inferred(H + 4, "cm", 0.7, "internal_plus_4cm_default")

    swl_match = _find_number(r"(?:swl|safe working load|load)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:kg|kgs)?", text)
    swl = env(swl_match[0], "kg", FieldStatus.PROVIDED, 0.96, swl_match[1]) if swl_match else missing("kg")

    sf_match = re.search(r"(?:sf|safety factor)\s*[:\-]?\s*(\d+)(?:\s*:?\s*0?1)?", text, re.IGNORECASE)
    sf = env(float(sf_match.group(1)), None, FieldStatus.PROVIDED, 0.96, sf_match.group(0)) if sf_match else missing()

    weight_match = re.search(r"(?:target weight|bag weight|weight)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(kg|g|gm|gram)?", text, re.IGNORECASE)
    if weight_match:
        value = float(weight_match.group(1))
        unit = (weight_match.group(2) or "g").lower()
        grams = value * 1000 if unit == "kg" else value
        target_weight = env(grams, "g", FieldStatus.PROVIDED, 0.85, weight_match.group(0))
    else:
        target_weight = not_specified("g")

    color = not_specified(None, "WHITE")
    if _contains_any(low, ["m white", "milky white", "m/white"]):
        color = env("M/WHITE", None, FieldStatus.PROVIDED, 0.9, "m white")
    elif "white" in low:
        color = env("WHITE", None, FieldStatus.PROVIDED, 0.9, "white")
    elif "black" in low:
        color = env("BLACK", None, FieldStatus.PROVIDED, 0.9, "black")
    elif "natural" in low:
        color = env("NATURAL", None, FieldStatus.PROVIDED, 0.9, "natural")

    body_laminated = not_specified(None, False)
    if _contains_any(low, ["unlaminated", "without lam", "no lamination"]):
        body_laminated = env(False, None, FieldStatus.PROVIDED, 0.92, "unlaminated")
    elif _contains_any(low, ["laminated", "lamination", "lami"]):
        body_laminated = env(True, None, FieldStatus.PROVIDED, 0.9, "laminated")

    top_type = not_specified(None, "OPEN_TOP")
    if "top panel" in low or "closed top" in low:
        top_type = env("TOP_PANEL", None, FieldStatus.PROVIDED, 0.92, "top panel")
    elif "skirt" in low or "duffle" in low:
        top_type = env("SKIRT", None, FieldStatus.PROVIDED, 0.92, "skirt")
    elif "top flap" in low:
        top_type = env("TOP_FLAP", None, FieldStatus.PROVIDED, 0.9, "top flap")
    elif "open top" in low:
        top_type = env("OPEN_TOP", None, FieldStatus.PROVIDED, 0.9, "open top")

    has_ds = _bool_field(low, ["discharge spout", "d/s", "ds spout", "bottom spout"], ["flat bottom", "no ds", "without discharge"], False)
    bottom_type = env("DISCHARGE_SPOUT", None, FieldStatus.INFERRED, 0.8, None, "has_ds_spout") if has_ds.value else not_specified(None, "FLAT_BOTTOM")
    if "flat bottom" in low:
        bottom_type = env("FLAT_BOTTOM", None, FieldStatus.PROVIDED, 0.95, "flat bottom")
    if "iris" in low or "irish" in low:
        bottom_type = env("IRIS", None, FieldStatus.PROVIDED, 0.9, "iris")

    has_fs = _bool_field(low, ["filling spout", "f/s", "fs spout", "top spout"], ["no fs", "without filling"], False)
    has_baffle = _bool_field(low, ["baffle", "q bag", "anti bulge"], ["no baffle", "without baffle"], False)
    has_liner = _bool_field(low, ["liner", "ldpe"], ["no liner", "without liner"], False)
    has_doc = _bool_field(low, ["doc pocket", "document pocket", "doc"], ["no doc", "without doc"], False)
    has_ddp = _bool_field(low, ["ddp", "dust proof", "double dust"], ["no ddp", "without ddp"], False)

    fs_dia = _find_number(r"(?:fs|filling spout|top spout).*?(\d+(?:\.\d+)?)\s*(?:dia|diameter|cm)", text)
    fs_h = _find_number(r"(?:fs|filling spout|top spout).*?(?:x|by)\s*(\d+(?:\.\d+)?)\s*cm", text)
    ds_dia = _find_number(r"(?:ds|d/s|discharge spout|bottom spout).*?(\d+(?:\.\d+)?)\s*(?:dia|diameter|cm)", text)
    ds_h = _find_number(r"(?:ds|d/s|discharge spout|bottom spout).*?(?:x|by)\s*(\d+(?:\.\d+)?)\s*cm", text)

    loop_qty_match = _find_number(r"(\d+)\s*(?:corner\s*)?loops?", text)
    loop_width_match = _find_number(r"(?:loop|belt).*?(\d+(?:\.\d+)?)\s*mm", text)
    ll_match = _find_number(r"\bLL\s*[:\-]?\s*(\d+(?:\.\d+)?)", text)
    sl_match = _find_number(r"\bSL\s*[:\-]?\s*(\d+(?:\.\d+)?)", text)
    print_sides = 0 if _contains_any(low, ["no printing", "without printing", "unprinted"]) else None

    spec = StructuredSpec(
        spec_id=f"spec-{uuid4()}",
        source_query_id=raw.query_id,
        customer=not_specified(),
        ref_no=not_specified(),
        bag_type=bag_type,
        dimensions=DimensionsSpec(int_L=int_L, int_W=int_W, int_H=int_H, ext_L=ext_L, ext_W=ext_W, ext_H=ext_H),
        swl_kg=swl,
        sf=sf,
        bag_weight_target_g=target_weight,
        fabric_color=color,
        body_laminated=body_laminated,
        double_layer=not_specified(None, False),
        top_type=top_type,
        bottom_type=bottom_type,
        loop=LoopSpec(
            loop_family=inferred("corner_loop", None, 0.8, "u_panel_default") if bag_type.value == "u_panel" else not_specified(),
            loop_qty=env(loop_qty_match[0], None, FieldStatus.PROVIDED, 0.9, loop_qty_match[1]) if loop_qty_match else not_specified(None, 4),
            loop_width_mm=env(loop_width_match[0], "mm", FieldStatus.PROVIDED, 0.9, loop_width_match[1]) if loop_width_match else not_specified("mm"),
            loop_LL_cm=env(ll_match[0], "cm", FieldStatus.PROVIDED, 0.9, ll_match[1]) if ll_match else not_specified("cm"),
            loop_SL_cm=env(sl_match[0], "cm", FieldStatus.PROVIDED, 0.9, sl_match[1]) if sl_match else not_specified("cm"),
            loop_color=inferred(color.value, None, 0.65, "same_as_body_color"),
            free_height_cm=not_specified("cm"),
        ),
        accessories=AccessorySpec(
            has_fs_spout=has_fs,
            fs_spout_dia_cm=env(fs_dia[0], "cm", FieldStatus.PROVIDED, 0.85, fs_dia[1]) if fs_dia else not_specified("cm"),
            fs_spout_h_cm=env(fs_h[0], "cm", FieldStatus.PROVIDED, 0.85, fs_h[1]) if fs_h else not_specified("cm"),
            has_ds_spout=has_ds,
            ds_spout_dia_cm=env(ds_dia[0], "cm", FieldStatus.PROVIDED, 0.85, ds_dia[1]) if ds_dia else not_specified("cm"),
            ds_spout_h_cm=env(ds_h[0], "cm", FieldStatus.PROVIDED, 0.85, ds_h[1]) if ds_h else not_specified("cm"),
            ds_closure=env("IRIS", None, FieldStatus.PROVIDED, 0.9, "iris") if "iris" in low or "irish" in low else not_specified(),
            has_baffle=has_baffle,
            has_liner=has_liner,
            liner_micron=not_specified("micron"),
            has_doc_pocket=has_doc,
            doc_pocket_size=env("10x12 inch", None, FieldStatus.PROVIDED, 0.8, "10x12") if "10" in low and "12" in low and "doc" in low else not_specified(),
            has_ddp=has_ddp,
            has_stevedore=not_specified(None, False),
        ),
        printing=PrintingSpec(
            printing_sides=env(print_sides, None, FieldStatus.PROVIDED, 0.9, "no printing") if print_sides == 0 else not_specified(None, 0),
            printing_colors=env(0, None, FieldStatus.PROVIDED, 0.9, "no printing") if print_sides == 0 else not_specified(None, 0),
            printing_color_names=env([], None, FieldStatus.INAPPLICABLE, 1.0, None, None) if print_sides == 0 else not_specified(None, []),
        ),
        notes=[],
    )
    return NormalizationResult(structured_spec=spec, changes=changes)


def raw_query_from_text(text: str, query_id: str | None = None) -> CustomerQueryRaw:
    return CustomerQueryRaw(
        query_id=query_id or f"query-{uuid4()}",
        language_hint="mixed",
        raw_text=text,
        attachments=[],
        received_at=datetime.now(),
    )
