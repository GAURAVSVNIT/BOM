"""JSON Schemas for grammar-constrained decoding (vLLM `guided_json`, plan §9.3).

Built from the live rule book (`03_DATASET/build/rules.py`) and a real gold row,
so the schema can never drift from the data:

  * adapter A -> OrderSpec: fixed keys, every value is `{value, state}`
  * adapter B -> BuildSpec: ~70 keys, enums pinned from `rules.ENUMS` /
    catalogues, plus the `{build_spec, clarification}` wrapper the conflict rows use

"What the grammar CANNOT express" (cross-field: body_gsm >= envelope floor,
belt_gpm inside the load band, mandatory component set) stays a job for the
validation gate — see plan §7. This module only enforces *shape and vocabulary*.
"""
from __future__ import annotations
import importlib.util
import json
from functools import lru_cache

from .paths import rules_module_path, gold_jsonl


@lru_cache(maxsize=1)
def _rules():
    spec = importlib.util.spec_from_file_location("bom_rules", rules_module_path())
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── adapter A : OrderSpec ───────────────────────────────────────────────
_ORDER_NUMERIC = {
    "ext_L_cm", "ext_W_cm", "ext_H_cm", "int_L_cm", "int_W_cm", "int_H_cm",
    "swl_kg", "order_qty", "req_weight_g", "quoted_weight_g", "loop_qty",
    "loop_free_height_cm", "loop_LL_cm", "loop_SL_cm", "belt_width_mm",
    "fs_dia_cm", "fs_height_cm", "ds_dia_cm", "ds_height_cm", "liner_micron",
    "printing_sides", "stated_body_gsm",
}
_ORDER_BOOL = {"has_liner", "has_doc_pocket", "has_printing"}
_ORDER_STR = {
    "customer", "sf", "stated_bag_type_raw", "fabric_colour", "loop_colour",
    "top_type", "fs_closure", "bottom_type", "ds_closure", "packing",
    "product_contents", "static_type", "order_no",
}
STATES = ["provided", "not_specified", "derived", "repaired"]


def _field(kind: str) -> dict:
    if kind == "number":
        val = {"type": ["number", "null"]}
    elif kind == "boolean":
        val = {"type": ["boolean", "null"]}
    else:
        val = {"type": ["string", "null"]}
    return {
        "type": "object",
        "properties": {"value": val, "state": {"enum": STATES},
                       "evidence": {"type": "string"}, "source": {"type": "string"}},
        "required": ["value", "state"],
        "additionalProperties": False,
    }


@lru_cache(maxsize=1)
def order_spec_schema() -> dict:
    keys = set(_ORDER_NUMERIC) | _ORDER_BOOL | _ORDER_STR
    props = {"source_type": {"type": "string"}}
    for k in sorted(keys):
        kind = ("number" if k in _ORDER_NUMERIC
                else "boolean" if k in _ORDER_BOOL else "string")
        props[k] = _field(kind)
    return {
        "type": "object", "title": "OrderSpec",
        "properties": props,
        "required": sorted(keys),
        "additionalProperties": False,
    }


# ── adapter B : BuildSpec ───────────────────────────────────────────────
@lru_cache(maxsize=1)
def _gold_build_row() -> dict:
    with gold_jsonl("build_spec").open(encoding="utf-8") as f:
        row = json.loads(f.readline())
    return {k: v for k, v in row.items() if not k.startswith("_")}


# rules.ENUMS key  ->  BuildSpec field name(s) it constrains
_ENUM_FIELD = {
    "family": ["family"],
    "loop_type": ["loop_type"],
    "static_type": ["static_type"],
    "top_type": ["top_type"],
    "bottom_type": ["bottom_type"],
    "closure": ["fs_closure", "ds_closure"],
    "dust_proof": ["dust_proof"],
    "liner_insertion": ["liner_insertion"],
    "fabric_type": ["fabric_type"],
    "baffle_pattern": ["baffle_pattern"],
    "punch_type": ["punch_type"],
    "stitch_machine": ["stitch_machine"],
    "stitch_spec": ["stitch_spec"],
    "fold_spec": ["fold_spec"],
    "fold_mode": ["fold_mode"],
    "body_gsm": ["body_gsm", "bottom_gsm", "top_gsm"],
    "belt_width_mm": ["belt_width_mm"],
    "belt_gpm": ["belt_gpm"],
    "loop_qty": ["loop_qty"],
    "yarn_white_denier": ["yarn_white_denier"],
    "yarn_blue_denier": ["yarn_blue_denier"],
}


def _value_schema_for(field: str, sample_value, enum_map: dict) -> dict:
    if field in enum_map:
        vals = list(enum_map[field])
        # allow null too: many BuildSpec fields are legitimately null
        return {"anyOf": [{"enum": vals}, {"type": "null"}]}
    if isinstance(sample_value, bool):
        return {"type": "boolean"}
    if isinstance(sample_value, (int, float)):
        return {"type": ["number", "null"]}
    if isinstance(sample_value, list):
        return {"type": "array"}
    if isinstance(sample_value, dict):
        return {"type": "object"}
    return {"type": ["string", "null"]}


@lru_cache(maxsize=1)
def build_spec_schema() -> dict:
    R = _rules()
    row = _gold_build_row()
    enum_map: dict[str, list] = {}
    for enum_key, flds in _ENUM_FIELD.items():
        if enum_key in R.ENUMS:
            for f in flds:
                enum_map[f] = R.ENUMS[enum_key]
    props = {}
    for k, v in row.items():
        props[k] = _value_schema_for(k, v, enum_map)
    return {
        "type": "object", "title": "BuildSpec",
        "properties": props,
        "required": [k for k in row if not isinstance(row[k], dict)],
        "additionalProperties": True,   # tolerate new BuildSpec fields (plan §13)
    }


@lru_cache(maxsize=1)
def build_output_schema() -> dict:
    """What adapter B may emit: a bare BuildSpec, or {build_spec, clarification}."""
    bs = build_spec_schema()
    wrapped = {
        "type": "object",
        "properties": {
            "build_spec": bs,
            "clarification": {"type": ["object", "null"]},
        },
        "required": ["build_spec"],
        "additionalProperties": False,
    }
    return {"anyOf": [bs, wrapped]}


def guided_json(adapter: str) -> dict:
    return order_spec_schema() if adapter == "a" else build_output_schema()


if __name__ == "__main__":
    import sys
    ad = sys.argv[1] if len(sys.argv) > 1 else "a"
    print(json.dumps(guided_json(ad), indent=2)[:4000])
