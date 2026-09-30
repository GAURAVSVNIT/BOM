# System Contract

Status: frozen for Sprint 1.

This document defines the object contracts used across the BOM generator. All
pipeline modules must consume and produce these shapes. Implementation code must
not introduce a second shape.

## Shared Conventions

### Units

- Length: `cm`
- Width: `cm`, except loop/tape width also exposed as `mm` where the source uses mm.
- Weight: `g`
- SWL: `kg`
- GSM for fabric: `g/m2`, stored as `gsm_area`.
- GSM for tape/loop/tie/DDP: `g/m`, stored as `gsm_per_m`.

### Field State

Every optional customer-intent field must carry one of:

- `provided`: explicitly present in customer query or source sheet.
- `inferred`: inferred from another field with a named rule.
- `missing`: expected but not found.
- `not_specified`: explicitly blank or customer did not provide it.
- `inapplicable`: does not apply to the bag type.

### Confidence

Every normalized field from NLP gets:

```json
{
  "value": 1000,
  "unit": "kg",
  "status": "provided",
  "confidence": 0.97,
  "source_text": "1000 kg"
}
```

Rule-engine fields do not use confidence. They use `rule_hits`.

## Object 1: CustomerQueryRaw

Raw user input before normalization.

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
  "received_at": "ISO-8601 string"
}
```

Rules:

- Never write engineered BOM values here.
- Preserve raw text exactly for audit.

## Object 2: StructuredSpec

Output of Sarvam LLM plus deterministic normalization. Contains customer intent
only. It must not contain chosen component GSMs, cut lengths, or computed
weights unless the customer explicitly supplied them.

```json
{
  "spec_id": "uuid",
  "source_query_id": "uuid",
  "customer": {"value": "string|null", "status": "provided|missing|not_specified", "confidence": 0.0},
  "ref_no": {"value": "string|null", "status": "provided|missing|not_specified", "confidence": 0.0},
  "bag_type": {"value": "u_panel|circular|four_panel|four_panel_baffle|two_panel|single_loop|two_loop|tubular|omega|platen|box|tunnel|container|conductive|null", "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
  "dimensions": {
    "int_L": {"value": 90.0, "unit": "cm", "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
    "int_W": {"value": 90.0, "unit": "cm", "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
    "int_H": {"value": 100.0, "unit": "cm", "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
    "ext_L": {"value": 94.0, "unit": "cm", "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
    "ext_W": {"value": 94.0, "unit": "cm", "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
    "ext_H": {"value": 104.0, "unit": "cm", "status": "provided|inferred|missing|not_specified", "confidence": 0.0}
  },
  "swl_kg": {"value": 1000.0, "unit": "kg", "status": "provided|missing|not_specified", "confidence": 0.0},
  "sf": {"value": 5, "status": "provided|missing|not_specified", "confidence": 0.0},
  "bag_weight_target_g": {"value": 1250.0, "unit": "g", "status": "provided|missing|not_specified", "confidence": 0.0},
  "fabric_color": {"value": "WHITE|M/WHITE|NATURAL|BLACK|BLUE|GREEN|TRANSPARENT|other|null", "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
  "top_type": {"value": "TOP_PANEL|SKIRT|OPEN_TOP|DUFFLE|TOP_FLAP|null", "status": "provided|inferred|missing|not_specified|inapplicable", "confidence": 0.0},
  "bottom_type": {"value": "FLAT_BOTTOM|DISCHARGE_SPOUT|IRIS|PETAL|CLOSED_BOTTOM|null", "status": "provided|inferred|missing|not_specified|inapplicable", "confidence": 0.0},
  "loop": {
    "loop_family": {"value": "corner_loop|cross_corner_loop|full_body_loop|single_loop|two_loop|none|null", "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
    "loop_qty": {"value": 4, "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
    "loop_width_mm": {"value": 50.0, "unit": "mm", "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
    "loop_LL_cm": {"value": 80.0, "unit": "cm", "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
    "loop_SL_cm": {"value": 60.0, "unit": "cm", "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
    "loop_color": {"value": "WHITE|BLACK|BLUE|GREEN|YELLOW|other|null", "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
    "free_height": {"value": false, "status": "provided|inferred|missing|not_specified", "confidence": 0.0}
  },
  "accessories": {
    "has_fs_spout": {"value": true, "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
    "fs_spout_w_cm": {"value": 40.0, "unit": "cm", "status": "provided|inferred|missing|not_specified|inapplicable", "confidence": 0.0},
    "fs_spout_h_cm": {"value": 50.0, "unit": "cm", "status": "provided|inferred|missing|not_specified|inapplicable", "confidence": 0.0},
    "has_ds_spout": {"value": true, "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
    "ds_spout_w_cm": {"value": 40.0, "unit": "cm", "status": "provided|inferred|missing|not_specified|inapplicable", "confidence": 0.0},
    "ds_spout_h_cm": {"value": 50.0, "unit": "cm", "status": "provided|inferred|missing|not_specified|inapplicable", "confidence": 0.0},
    "ds_closure": {"value": "IRIS|PETAL|TIE|OPEN|null", "status": "provided|inferred|missing|not_specified|inapplicable", "confidence": 0.0},
    "has_baffle": {"value": false, "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
    "has_liner": {"value": false, "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
    "liner_micron": {"value": 70.0, "unit": "micron", "status": "provided|inferred|missing|not_specified|inapplicable", "confidence": 0.0},
    "has_doc_pocket": {"value": false, "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
    "doc_pocket_size": {"value": "A4|10x12 inch|11x12 inch|null", "status": "provided|inferred|missing|not_specified|inapplicable", "confidence": 0.0},
    "has_ddp": {"value": false, "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
    "has_stevedore": {"value": false, "status": "provided|inferred|missing|not_specified", "confidence": 0.0}
  },
  "printing": {
    "printing_sides": {"value": 0, "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
    "printing_colors": {"value": 0, "status": "provided|inferred|missing|not_specified", "confidence": 0.0},
    "printing_color_names": {"value": ["BLUE", "GREEN"], "status": "provided|inferred|missing|not_specified", "confidence": 0.0}
  },
  "notes": ["string"]
}
```

## Object 3: PhysicalBOM

Output of deterministic rule engine and final LLM synthesis. This is the stable
BOM contract.

```json
{
  "bom_id": "uuid",
  "source": "rule_engine|llm_synthesis|fallback_rule_engine",
  "source_spec_id": "uuid",
  "source_file": "string|null",
  "source_sheet": "string|null",
  "customer": "string|null",
  "ref_no": "string|null",
  "bag_type": "u_panel|circular|four_panel|four_panel_baffle|two_panel|single_loop|two_loop|tubular|omega|platen|box|tunnel|container|conductive|null",
  "swl_kg": 1000.0,
  "sf": 5,
  "ext_L": 94.0,
  "ext_W": 94.0,
  "ext_H": 104.0,
  "int_L": 90.0,
  "int_W": 90.0,
  "int_H": 100.0,
  "bag_weight_target_g": 1250.0,
  "bag_weight_actual_g": 1253.452,
  "computed_total_g": 1253.452,
  "components": [
    {
      "sr": 1,
      "canonical_name": "BODY PANEL",
      "original_name": "BODY PANEL|null",
      "gsm_area": 140.0,
      "gsm_per_m": null,
      "lami_ul": "LAMINATED|UNLAMINATED|PP|LDPE|BSL|null",
      "color": "WHITE|M/WHITE|NATURAL|BLACK|BLUE|GREEN|TRANSPARENT|other|null",
      "width_cm": 102.0,
      "cut_cm": 310.0,
      "qty": 1,
      "weight_g": 442.68,
      "remark": "string|null"
    }
  ],
  "assumptions": [
    {"id": "A001", "field": "ext_dims", "assumption": "external dimensions inferred as internal + 4cm", "basis": "dimension_default_rule"}
  ],
  "rule_hits": [
    {"rule_id": "U_PANEL_BODY_GEOM_001", "severity": "hard_constraint", "component": "BODY PANEL"}
  ],
  "constraint_inputs": {
    "design_load_kg": 5000.0,
    "selected_gsm_basis": "image_gsm_table|dataset_mode|fallback",
    "loom_width_table_version": "2026-05-26",
    "gsm_table_version": "2026-05-26"
  }
}
```

Rules:

- `bag_weight_target_g` is customer quoted/spec weight.
- `bag_weight_actual_g` is source grand total or generated BOM total.
- `computed_total_g` is sum of component `weight_g`.
- In generated BOMs, `bag_weight_actual_g` and `computed_total_g` must match.
- In extracted historical BOMs, keep both even if source grand total and component sum need audit.

## Object 4: RetrievedBOM

Structured retrieval result. Never return only text chunks.

```json
{
  "retrieval_id": "uuid",
  "source_file": "string",
  "source_sheet": "string",
  "record_index": 123,
  "score_total": 0.91,
  "score_breakdown": {
    "geometric": 0.42,
    "categorical": 0.34,
    "semantic": 0.15
  },
  "why_matched": [
    "same bag_type u_panel",
    "internal dimensions within 5cm",
    "same SWL/SF",
    "same skirt/open-bottom configuration"
  ],
  "spec_snapshot": {},
  "component_list": [],
  "bag_weight_target_g": 1250.0,
  "bag_weight_actual_g": 1253.452
}
```

## Object 5: ValidationReport

Machine-readable validation result. No prose-only errors.

```json
{
  "schema_pass": true,
  "hard_failures": [
    {
      "code": "FORBIDDEN_LOOM_WIDTH",
      "path": "components[0].width_cm",
      "message": "Width 101cm is not in loom_width_table.",
      "allowed_values": [98, 100, 102, 103, 105],
      "actual_value": 101
    }
  ],
  "soft_warnings": [
    {
      "code": "TARGET_ACTUAL_WEIGHT_GAP",
      "path": "bag_weight_target_g",
      "message": "Target differs from BOM actual by 11.1%.",
      "actual_value": 3100,
      "reference_value": 2756.16
    }
  ],
  "retriable": true,
  "error_context_for_llm": {
    "fix_only_these_paths": ["components[0].width_cm"],
    "do_not_change_paths": ["bag_type", "int_L", "int_W", "int_H"]
  },
  "final_decision": "pass|pass_with_warnings|retry|fallback_rule_engine|reject"
}
```

## Object 6: AuditTrail

Persisted for every generation.

```json
{
  "run_id": "uuid",
  "raw_query": {},
  "structured_spec": {},
  "normalization_changes": [],
  "rule_engine_bom": {},
  "rule_hits": [],
  "retrieved_boms": [],
  "llm_prompt_version": "synthesis_v1",
  "llm_raw_output": {},
  "validation_reports": [],
  "retry_count": 0,
  "final_bom": {},
  "final_pass_fail": "pass|pass_with_warnings|fallback|reject",
  "created_at": "ISO-8601 string"
}
```

## Object 7: FinalBOMPackage

The final output object returned to the UI/API.

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
    "bag_weight_target_g": 1250.0,
    "bag_weight_actual_g": 1253.452,
    "warnings_count": 0,
    "retrieved_examples_used": 3
  },
  "provenance": {
    "rule_table_versions": ["gsm_thresholds:2026-05-26", "loom_widths:2026-05-26"],
    "retrieved_sources": ["file.xlsx::sheet"],
    "model_name": "qwen-finetuned|null"
  }
}
```

