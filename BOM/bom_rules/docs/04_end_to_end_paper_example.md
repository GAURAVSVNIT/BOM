# End-To-End Paper Example

This example is not executable code. It freezes the intended data flow.

## Raw Customer Query

```text
Mujhe 90 x 90 x 100 cm U+2 panel bag chahiye.
SWL 1000 kg, SF 5:1, top skirt 80 cm, flat bottom.
Loop 4x30, LL 65, SL 35, M white fabric, no printing.
Target weight customer ne nahi diya.
```

## CustomerQueryRaw

```json
{
  "query_id": "demo-001",
  "language_hint": "mixed",
  "raw_text": "Mujhe 90 x 90 x 100 cm U+2 panel bag chahiye. SWL 1000 kg, SF 5:1, top skirt 80 cm, flat bottom. Loop 4x30, LL 65, SL 35, M white fabric, no printing. Target weight customer ne nahi diya.",
  "attachments": [],
  "received_at": "2026-05-26T00:00:00+05:30"
}
```

## StructuredSpec

```json
{
  "spec_id": "demo-spec-001",
  "source_query_id": "demo-001",
  "bag_type": {"value": "u_panel", "status": "provided", "confidence": 0.95, "source_text": "U+2 panel"},
  "dimensions": {
    "int_L": {"value": 90, "unit": "cm", "status": "provided", "confidence": 0.96, "source_text": "90 x 90 x 100"},
    "int_W": {"value": 90, "unit": "cm", "status": "provided", "confidence": 0.96, "source_text": "90 x 90 x 100"},
    "int_H": {"value": 100, "unit": "cm", "status": "provided", "confidence": 0.96, "source_text": "90 x 90 x 100"},
    "ext_L": {"value": 94, "unit": "cm", "status": "inferred", "confidence": 0.75, "source_text": null},
    "ext_W": {"value": 94, "unit": "cm", "status": "inferred", "confidence": 0.75, "source_text": null},
    "ext_H": {"value": 104, "unit": "cm", "status": "inferred", "confidence": 0.75, "source_text": null}
  },
  "swl_kg": {"value": 1000, "unit": "kg", "status": "provided", "confidence": 0.98, "source_text": "SWL 1000 kg"},
  "sf": {"value": 5, "status": "provided", "confidence": 0.98, "source_text": "SF 5:1"},
  "bag_weight_target_g": {"value": null, "unit": "g", "status": "not_specified", "confidence": 1.0, "source_text": "Target weight customer ne nahi diya"},
  "fabric_color": {"value": "M/WHITE", "status": "provided", "confidence": 0.90, "source_text": "M white"},
  "top_type": {"value": "SKIRT", "status": "provided", "confidence": 0.95, "source_text": "top skirt 80 cm"},
  "bottom_type": {"value": "FLAT_BOTTOM", "status": "provided", "confidence": 0.95, "source_text": "flat bottom"},
  "loop": {
    "loop_family": {"value": "corner_loop", "status": "inferred", "confidence": 0.80, "source_text": "U+2 panel"},
    "loop_qty": {"value": 4, "status": "provided", "confidence": 0.95, "source_text": "4x30"},
    "loop_width_mm": {"value": 40, "unit": "mm", "status": "inferred", "confidence": 0.70, "source_text": null},
    "loop_LL_cm": {"value": 65, "unit": "cm", "status": "provided", "confidence": 0.95, "source_text": "LL 65"},
    "loop_SL_cm": {"value": 35, "unit": "cm", "status": "provided", "confidence": 0.95, "source_text": "SL 35"},
    "loop_color": {"value": "M/WHITE", "status": "inferred", "confidence": 0.60, "source_text": null},
    "free_height": {"value": false, "status": "not_specified", "confidence": 1.0, "source_text": null}
  },
  "accessories": {
    "has_fs_spout": {"value": false, "status": "not_specified", "confidence": 0.80},
    "has_ds_spout": {"value": false, "status": "provided", "confidence": 0.95},
    "has_baffle": {"value": false, "status": "inferred", "confidence": 0.80},
    "has_liner": {"value": false, "status": "not_specified", "confidence": 0.80},
    "has_doc_pocket": {"value": false, "status": "not_specified", "confidence": 0.80},
    "has_ddp": {"value": false, "status": "not_specified", "confidence": 0.80},
    "has_stevedore": {"value": false, "status": "not_specified", "confidence": 0.80}
  },
  "printing": {
    "printing_sides": {"value": 0, "status": "provided", "confidence": 0.95, "source_text": "no printing"},
    "printing_colors": {"value": 0, "status": "provided", "confidence": 0.95, "source_text": "no printing"},
    "printing_color_names": {"value": [], "status": "inapplicable", "confidence": 1.0}
  },
  "notes": []
}
```

## Deterministic PhysicalBOM Draft

```json
{
  "bom_id": "demo-rule-bom-001",
  "source": "rule_engine",
  "bag_type": "u_panel",
  "swl_kg": 1000,
  "sf": 5,
  "ext_L": 94,
  "ext_W": 94,
  "ext_H": 104,
  "int_L": 90,
  "int_W": 90,
  "int_H": 100,
  "bag_weight_target_g": null,
  "bag_weight_actual_g": 1253.452,
  "computed_total_g": 1253.452,
  "components": [
    {"sr": 1, "canonical_name": "BODY PANEL", "gsm_area": 140, "gsm_per_m": null, "lami_ul": "UNLAMINATED", "color": "M/WHITE", "width_cm": 102, "cut_cm": 310, "qty": 1, "weight_g": 442.68, "remark": null},
    {"sr": 2, "canonical_name": "SIDE PANEL", "gsm_area": 140, "gsm_per_m": null, "lami_ul": "UNLAMINATED", "color": "M/WHITE", "width_cm": 102, "cut_cm": 112, "qty": 2, "weight_g": 319.872, "remark": null},
    {"sr": 3, "canonical_name": "SKIRT", "gsm_area": 70, "gsm_per_m": null, "lami_ul": "LAMINATED", "color": "M/WHITE", "width_cm": 85, "cut_cm": 370, "qty": 1, "weight_g": 220.15, "remark": "80cm skirt"},
    {"sr": 4, "canonical_name": "FS TIE", "gsm_area": null, "gsm_per_m": 7, "lami_ul": "PP", "color": "M/WHITE", "width_cm": 1.5, "cut_cm": 125, "qty": 1, "weight_g": 8.75, "remark": null},
    {"sr": 5, "canonical_name": "CORNER LOOP", "gsm_area": null, "gsm_per_m": 30, "lami_ul": "PP", "color": "M/WHITE", "width_cm": 4, "cut_cm": 160, "qty": 4, "weight_g": 192.0, "remark": "LL=65 SL=35"},
    {"sr": 6, "canonical_name": "DOC POCKET", "gsm_area": 65, "gsm_per_m": null, "lami_ul": null, "color": "NATURAL", "width_cm": 25, "cut_cm": 35, "qty": 1, "weight_g": 12.0, "remark": "optional from retrieval only"},
    {"sr": 7, "canonical_name": "LABEL", "gsm_area": null, "gsm_per_m": null, "lami_ul": null, "color": null, "width_cm": null, "cut_cm": null, "qty": 1, "weight_g": 3.0, "remark": null},
    {"sr": 8, "canonical_name": "STITCHING", "gsm_area": null, "gsm_per_m": null, "lami_ul": null, "color": null, "width_cm": null, "cut_cm": null, "qty": 1, "weight_g": 55.0, "remark": "thread"}
  ],
  "assumptions": [
    {"id": "A001", "field": "ext_dims", "assumption": "external dimensions inferred as internal + 4cm", "basis": "dimension_default_rule"},
    {"id": "A002", "field": "loop_width_mm", "assumption": "40mm selected from corner loop table for SWL 1000 SF5", "basis": "belt_gpm_table"}
  ],
  "rule_hits": [
    {"rule_id": "U_PANEL_MANDATORY_COMPONENTS", "severity": "hard_constraint"},
    {"rule_id": "U_PANEL_BODY_GEOMETRY", "severity": "hard_constraint"},
    {"rule_id": "CORNER_LOOP_BELT_TABLE", "severity": "default_preference"}
  ],
  "constraint_inputs": {
    "design_load_kg": 5000,
    "selected_gsm_basis": "gsm_vs_swl_sf_image_table",
    "loom_width_table_version": "2026-05-26",
    "gsm_table_version": "2026-05-26"
  }
}
```

## Top-3 Retrieval Result Format

```json
[
  {
    "source_file": "90 X 90 X 100 CM (NEW U+2).xlsx",
    "source_sheet": "Sheet1",
    "score_total": 0.96,
    "score_breakdown": {"geometric": 0.50, "categorical": 0.36, "semantic": 0.10},
    "why_matched": ["same dimensions", "same u_panel type", "same SWL/SF", "same skirt flat-bottom family"],
    "bag_weight_target_g": null,
    "bag_weight_actual_g": 1253.452,
    "component_list": "full component list"
  }
]
```

## LLM Synthesis Output Shape

```json
{
  "bom": {},
  "decision_rationale": [
    "Kept deterministic U-panel geometry because retrieved example is exact match."
  ],
  "differences_from_rule_engine": [],
  "borrowed_patterns_from_retrieval": [
    "Used skirt 70 GSM and 85x370cm from exact historical match."
  ],
  "open_uncertainties": [
    "Customer did not specify target bag weight."
  ]
}
```

## ValidationReport

```json
{
  "schema_pass": true,
  "hard_failures": [],
  "soft_warnings": [
    {
      "code": "TARGET_WEIGHT_NOT_SPECIFIED",
      "path": "bag_weight_target_g",
      "message": "Customer target weight was not specified; generated BOM actual is 1253.452g."
    }
  ],
  "retriable": false,
  "error_context_for_llm": {},
  "final_decision": "pass_with_warnings"
}
```

## FinalBOMPackage

```json
{
  "package_id": "demo-package-001",
  "final_bom": "PhysicalBOM",
  "validation_report": "ValidationReport",
  "audit_trail_path": "runs/demo-001/audit.json",
  "csv_path": "runs/demo-001/bom.csv",
  "xlsx_path": "runs/demo-001/bom.xlsx",
  "summary": {
    "bag_type": "u_panel",
    "bag_weight_target_g": null,
    "bag_weight_actual_g": 1253.452,
    "warnings_count": 1,
    "retrieved_examples_used": 1
  },
  "provenance": {
    "rule_table_versions": ["gsm_thresholds:2026-05-26", "loom_widths:2026-05-26"],
    "retrieved_sources": ["90 X 90 X 100 CM (NEW U+2).xlsx::Sheet1"],
    "model_name": null
  }
}
```

