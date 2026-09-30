# Sprint 1 Contracts

Status: frozen draft for review.

These contracts are the boundary between extractor, normalizer, rule engine,
retrieval, LLM synthesis, validation, audit, and output packaging. No module
should invent a second shape.

## Shared Types

### Field Envelope

Every customer-intent field is wrapped in a field envelope:

```json
{
  "value": "any|null",
  "unit": "cm|g|kg|mm|micron|null",
  "status": "provided|inferred|missing|not_specified|inapplicable",
  "confidence": 0.0,
  "source_text": "string|null",
  "source": "customer_text|attachment_ocr|sheet|normalization_rule|null"
}
```

Rules:

- `provided`: explicitly stated by customer/source.
- `inferred`: derived by a named deterministic rule.
- `missing`: required for generation but absent.
- `not_specified`: customer did not specify and the field is optional.
- `inapplicable`: field cannot apply to the selected bag type/style.
- No free text after normalization except `notes`.

## CustomerQueryRaw

Raw input before extraction.

```json
{
  "query_id": "uuid",
  "language_hint": "hi|en|mixed|unknown",
  "raw_text": "string",
  "attachments": [
    {
      "attachment_id": "string",
      "kind": "image|pdf|xlsx|csv|other",
      "path": "string",
      "ocr_text": "string|null"
    }
  ],
  "received_at": "ISO-8601"
}
```

Constraint: preserve the customer text exactly for audit.

## StructuredSpec

Output of Sarvam extraction plus deterministic normalization. This object
contains only customer intent. It must not contain selected GSM, loom width,
component cut length, or computed weight unless that value was explicitly
provided by the customer/source.

### Field List

| Field | Type | Unit | Null status allowed | Extraction source |
|---|---|---:|---|---|
| `spec_id` | string | null | no | system |
| `source_query_id` | string | null | no | system |
| `customer` | FieldEnvelope[string] | null | missing, not_specified | text/sheet |
| `ref_no` | FieldEnvelope[string] | null | missing, not_specified | text/sheet |
| `bag_type` | FieldEnvelope[enum] | null | missing, not_specified | text/sheet/rule |
| `dimensions.int_L` | FieldEnvelope[number] | cm | missing | text/sheet |
| `dimensions.int_W` | FieldEnvelope[number] | cm | missing | text/sheet |
| `dimensions.int_H` | FieldEnvelope[number] | cm | missing | text/sheet |
| `dimensions.ext_L` | FieldEnvelope[number] | cm | missing, not_specified | text/sheet/rule |
| `dimensions.ext_W` | FieldEnvelope[number] | cm | missing, not_specified | text/sheet/rule |
| `dimensions.ext_H` | FieldEnvelope[number] | cm | missing, not_specified | text/sheet/rule |
| `swl_kg` | FieldEnvelope[number] | kg | missing | text/sheet |
| `sf` | FieldEnvelope[number] | null | missing | text/sheet |
| `bag_weight_target_g` | FieldEnvelope[number] | g | missing, not_specified | text/sheet |
| `fabric_color` | FieldEnvelope[enum] | null | missing, not_specified | text/sheet/rule |
| `body_laminated` | FieldEnvelope[boolean] | null | missing, not_specified | text/sheet |
| `double_layer` | FieldEnvelope[boolean] | null | not_specified | text/sheet |
| `top_type` | FieldEnvelope[enum] | null | missing, not_specified, inapplicable | text/sheet/rule |
| `bottom_type` | FieldEnvelope[enum] | null | missing, not_specified, inapplicable | text/sheet/rule |
| `loop.loop_family` | FieldEnvelope[enum] | null | missing, not_specified | text/sheet/rule |
| `loop.loop_qty` | FieldEnvelope[number] | null | missing, not_specified | text/sheet/rule |
| `loop.loop_width_mm` | FieldEnvelope[number] | mm | missing, not_specified | text/sheet/rule |
| `loop.loop_LL_cm` | FieldEnvelope[number] | cm | missing, not_specified | text/sheet |
| `loop.loop_SL_cm` | FieldEnvelope[number] | cm | missing, not_specified | text/sheet |
| `loop.loop_color` | FieldEnvelope[enum] | null | missing, not_specified | text/sheet/rule |
| `loop.free_height_cm` | FieldEnvelope[number] | cm | missing, not_specified, inapplicable | text/sheet |
| `accessories.has_fs_spout` | FieldEnvelope[boolean] | null | missing, not_specified | text/sheet/rule |
| `accessories.fs_spout_dia_cm` | FieldEnvelope[number] | cm | missing, not_specified, inapplicable | text/sheet |
| `accessories.fs_spout_h_cm` | FieldEnvelope[number] | cm | missing, not_specified, inapplicable | text/sheet |
| `accessories.has_ds_spout` | FieldEnvelope[boolean] | null | missing, not_specified | text/sheet/rule |
| `accessories.ds_spout_dia_cm` | FieldEnvelope[number] | cm | missing, not_specified, inapplicable | text/sheet |
| `accessories.ds_spout_h_cm` | FieldEnvelope[number] | cm | missing, not_specified, inapplicable | text/sheet |
| `accessories.ds_closure` | FieldEnvelope[enum] | null | missing, not_specified, inapplicable | text/sheet |
| `accessories.has_baffle` | FieldEnvelope[boolean] | null | missing, not_specified | text/sheet/rule |
| `accessories.has_liner` | FieldEnvelope[boolean] | null | missing, not_specified | text/sheet/rule |
| `accessories.liner_micron` | FieldEnvelope[number] | micron | missing, not_specified, inapplicable | text/sheet |
| `accessories.has_doc_pocket` | FieldEnvelope[boolean] | null | missing, not_specified | text/sheet/rule |
| `accessories.doc_pocket_size` | FieldEnvelope[enum] | null | missing, not_specified, inapplicable | text/sheet |
| `accessories.has_ddp` | FieldEnvelope[boolean] | null | missing, not_specified | text/sheet/rule |
| `accessories.has_stevedore` | FieldEnvelope[boolean] | null | missing, not_specified | text/sheet |
| `printing.printing_sides` | FieldEnvelope[number] | null | missing, not_specified | text/sheet |
| `printing.printing_colors` | FieldEnvelope[number] | null | missing, not_specified | text/sheet |
| `printing.printing_color_names` | FieldEnvelope[array] | null | not_specified, inapplicable | text/sheet |
| `notes` | string[] | null | yes | text/sheet |

Enums:

- `bag_type`: `u_panel`, `circular`, `four_panel`, `four_panel_baffle`,
  `two_panel`, `single_loop`, `two_loop`, `tubular`, `omega`, `platen`, `box`,
  `tunnel`, `container`, `conductive`.
- `top_type`: `OPEN_TOP`, `TOP_PANEL`, `SKIRT`, `DUFFLE`, `TOP_FLAP`.
- `bottom_type`: `FLAT_BOTTOM`, `DISCHARGE_SPOUT`, `IRIS`, `PETAL`,
  `CLOSED_BOTTOM`.
- `loop_family`: `corner_loop`, `cross_corner_loop`, `full_body_loop`,
  `single_loop`, `two_loop`, `none`.
- `ds_closure`: `IRIS`, `PETAL`, `TIE`, `OPEN`.

## PhysicalBOM

Output of deterministic rule engine and final LLM synthesis.

```json
{
  "bom_id": "uuid",
  "source": "rule_engine|llm_synthesis|fallback_rule_engine|historical",
  "source_spec_id": "uuid",
  "source_file": "string|null",
  "source_sheet": "string|null",
  "customer": "string|null",
  "ref_no": "string|null",
  "bag_type": "u_panel",
  "swl_kg": 1250.0,
  "sf": 5.0,
  "ext_L": 89.0,
  "ext_W": 89.0,
  "ext_H": 114.0,
  "int_L": 85.0,
  "int_W": 85.0,
  "int_H": 110.0,
  "bag_weight_target_g": 1500.0,
  "bag_weight_actual_g": 1507.956,
  "computed_total_g": 1507.956,
  "components": [],
  "candidate_optional_components": [],
  "assumptions": [],
  "rule_hits": [],
  "constraint_inputs": {}
}
```

### Component Schema

```json
{
  "sr": 1,
  "canonical_name": "BODY PANEL",
  "original_name": "BODY PANEL|null",
  "gsm_area": 160.0,
  "gsm_per_m": null,
  "lami_ul": "LAMINATED|UNLAMINATED|PP|LDPE|BSL|null",
  "color": "WHITE|M/WHITE|NATURAL|BLACK|BLUE|GREEN|TRANSPARENT|BEIGE|RED|YELLOW|ORANGE|BROWN|other|null",
  "width_cm": 97.0,
  "cut_cm": 320.0,
  "qty": 1.0,
  "weight_g": 496.64,
  "remark": "string|null",
  "source": "rule_engine|retrieval|llm|historical"
}
```

Rules:

- Fabric components use `gsm_area`.
- Tape, loop, tie, and DDP components use `gsm_per_m`.
- `bag_weight_target_g` is quoted/customer target.
- `bag_weight_actual_g` is generated total or historical source total.
- For generated BOMs, `bag_weight_actual_g` must equal `computed_total_g`
  within tolerance.
- Optional uncertain items go in `candidate_optional_components`, not in
  `components`.

## RetrievedBOM

Structured retrieval result. Never return only text chunks.

```json
{
  "retrieval_id": "uuid",
  "source_file": "string",
  "source_sheet": "string",
  "record_index": 0,
  "score_total": 0.0,
  "score_breakdown": {
    "geometric": 0.0,
    "categorical": 0.0,
    "semantic": 0.0
  },
  "why_matched": ["string"],
  "structured_spec_snapshot": {},
  "component_list": [],
  "bag_weight_target_g": 1500.0,
  "bag_weight_actual_g": 1506.273,
  "data_warnings": []
}
```

## ValidationReport

Machine-readable validation result. The retry loop consumes this object.

```json
{
  "schema_pass": true,
  "hard_failures": [
    {
      "code": "FORBIDDEN_LOOM_WIDTH",
      "path": "components[0].width_cm",
      "message": "Width 101cm is not approved for BODY PANEL.",
      "allowed_values": [98, 100, 102, 103, 105],
      "actual_value": 101
    }
  ],
  "soft_warnings": [
    {
      "code": "TARGET_ACTUAL_WEIGHT_GAP",
      "path": "bag_weight_target_g",
      "message": "Target differs from actual by more than 10 percent.",
      "actual_value": 1507.956,
      "reference_value": 1500.0
    }
  ],
  "retriable": true,
  "error_context_for_llm": {
    "fix_only_these_paths": ["components[0].width_cm"],
    "do_not_change_paths": ["bag_type", "swl_kg", "sf", "int_L", "int_W", "int_H"]
  },
  "final_decision": "pass|pass_with_warnings|retry|fallback_rule_engine|reject"
}
```

## AuditTrail

Persisted for every run.

```json
{
  "run_id": "uuid",
  "raw_query": {},
  "structured_spec": {},
  "normalization_changes": [],
  "rule_engine_bom": {},
  "rule_hits": [],
  "retrieved_boms": [],
  "llm_prompt_version": "synthesis_v1|null",
  "llm_raw_output": {},
  "validation_reports": [],
  "retry_count": 0,
  "final_bom": {},
  "final_pass_fail": "pass|pass_with_warnings|fallback|reject",
  "created_at": "ISO-8601"
}
```

## FinalBOMPackage

API/UI output object.

```json
{
  "package_id": "uuid",
  "final_bom": {},
  "validation_report": {},
  "audit_trail_path": "runs/<run_id>/audit.json",
  "csv_path": "runs/<run_id>/bom.csv",
  "xlsx_path": "runs/<run_id>/bom.xlsx",
  "summary": {
    "bag_type": "u_panel",
    "bag_weight_target_g": 1500.0,
    "bag_weight_actual_g": 1507.956,
    "warnings_count": 0,
    "retrieved_examples_used": 3
  },
  "provenance": {
    "rule_table_versions": ["hard_constraints:2026-05-26", "defaults:2026-05-26", "heuristics:2026-05-26"],
    "retrieved_sources": ["file.xlsx::sheet"],
    "model_name": "qwen-finetuned|null"
  }
}
```
