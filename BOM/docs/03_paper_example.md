# End-to-End Paper Example

This is not executable code. It freezes the intended shapes for Sprint 2. The
deterministic BOM below includes only components triggered by bag type, top
type, bottom/closure type, or explicit accessory flags. Retrieval-only optional
suggestions are not inserted into the deterministic BOM.

## Raw Customer Query

```text
85 x 85 x 110 cm internal U+2 panel bag. Outer approx 89 x 89 x 114.
SWL 1250 kg, SF 5:1. White unlaminated body. Top panel with 40 dia x
50 cm filling spout. Bottom discharge spout 35 dia x 50 cm with iris.
4 corner loops, 50 mm, LL 70, SL 50. Doc pocket 10 x 12 inch. Target
weight 1.5 kg. No printing.
```

## StructuredSpec

```json
{
  "spec_id": "demo-spec-001",
  "source_query_id": "demo-query-001",
  "bag_type": {"value": "u_panel", "unit": null, "status": "provided", "confidence": 0.97, "source_text": "U+2 panel", "source": "customer_text"},
  "dimensions": {
    "int_L": {"value": 85, "unit": "cm", "status": "provided", "confidence": 0.98, "source_text": "85 x 85 x 110 cm internal", "source": "customer_text"},
    "int_W": {"value": 85, "unit": "cm", "status": "provided", "confidence": 0.98, "source_text": "85 x 85 x 110 cm internal", "source": "customer_text"},
    "int_H": {"value": 110, "unit": "cm", "status": "provided", "confidence": 0.98, "source_text": "85 x 85 x 110 cm internal", "source": "customer_text"},
    "ext_L": {"value": 89, "unit": "cm", "status": "provided", "confidence": 0.94, "source_text": "Outer approx 89 x 89 x 114", "source": "customer_text"},
    "ext_W": {"value": 89, "unit": "cm", "status": "provided", "confidence": 0.94, "source_text": "Outer approx 89 x 89 x 114", "source": "customer_text"},
    "ext_H": {"value": 114, "unit": "cm", "status": "provided", "confidence": 0.94, "source_text": "Outer approx 89 x 89 x 114", "source": "customer_text"}
  },
  "swl_kg": {"value": 1250, "unit": "kg", "status": "provided", "confidence": 0.99, "source_text": "SWL 1250 kg", "source": "customer_text"},
  "sf": {"value": 5, "unit": null, "status": "provided", "confidence": 0.99, "source_text": "SF 5:1", "source": "customer_text"},
  "bag_weight_target_g": {"value": 1500, "unit": "g", "status": "provided", "confidence": 0.95, "source_text": "Target weight 1.5 kg", "source": "customer_text"},
  "fabric_color": {"value": "WHITE", "unit": null, "status": "provided", "confidence": 0.96, "source_text": "White", "source": "customer_text"},
  "body_laminated": {"value": false, "unit": null, "status": "provided", "confidence": 0.94, "source_text": "unlaminated body", "source": "customer_text"},
  "double_layer": {"value": false, "unit": null, "status": "not_specified", "confidence": 1.0, "source_text": null, "source": null},
  "top_type": {"value": "TOP_PANEL", "unit": null, "status": "provided", "confidence": 0.95, "source_text": "Top panel", "source": "customer_text"},
  "bottom_type": {"value": "DISCHARGE_SPOUT", "unit": null, "status": "provided", "confidence": 0.95, "source_text": "Bottom discharge spout", "source": "customer_text"},
  "loop": {
    "loop_family": {"value": "corner_loop", "unit": null, "status": "inferred", "confidence": 0.85, "source_text": "U+2 panel", "source": "normalization_rule"},
    "loop_qty": {"value": 4, "unit": null, "status": "provided", "confidence": 0.98, "source_text": "4 corner loops", "source": "customer_text"},
    "loop_width_mm": {"value": 50, "unit": "mm", "status": "provided", "confidence": 0.98, "source_text": "50 mm", "source": "customer_text"},
    "loop_LL_cm": {"value": 70, "unit": "cm", "status": "provided", "confidence": 0.98, "source_text": "LL 70", "source": "customer_text"},
    "loop_SL_cm": {"value": 50, "unit": "cm", "status": "provided", "confidence": 0.98, "source_text": "SL 50", "source": "customer_text"},
    "loop_color": {"value": "WHITE", "unit": null, "status": "inferred", "confidence": 0.70, "source_text": "White", "source": "normalization_rule"}
  },
  "accessories": {
    "has_fs_spout": {"value": true, "unit": null, "status": "provided", "confidence": 0.96, "source_text": "filling spout", "source": "customer_text"},
    "fs_spout_dia_cm": {"value": 40, "unit": "cm", "status": "provided", "confidence": 0.96, "source_text": "40 dia", "source": "customer_text"},
    "fs_spout_h_cm": {"value": 50, "unit": "cm", "status": "provided", "confidence": 0.96, "source_text": "50 cm filling spout", "source": "customer_text"},
    "has_ds_spout": {"value": true, "unit": null, "status": "provided", "confidence": 0.96, "source_text": "discharge spout", "source": "customer_text"},
    "ds_spout_dia_cm": {"value": 35, "unit": "cm", "status": "provided", "confidence": 0.96, "source_text": "35 dia", "source": "customer_text"},
    "ds_spout_h_cm": {"value": 50, "unit": "cm", "status": "provided", "confidence": 0.96, "source_text": "50 cm with iris", "source": "customer_text"},
    "ds_closure": {"value": "IRIS", "unit": null, "status": "provided", "confidence": 0.96, "source_text": "with iris", "source": "customer_text"},
    "has_baffle": {"value": false, "unit": null, "status": "inferred", "confidence": 0.80, "source_text": null, "source": "normalization_rule"},
    "has_liner": {"value": false, "unit": null, "status": "not_specified", "confidence": 0.80, "source_text": null, "source": null},
    "has_doc_pocket": {"value": true, "unit": null, "status": "provided", "confidence": 0.95, "source_text": "Doc pocket", "source": "customer_text"},
    "doc_pocket_size": {"value": "10x12 inch", "unit": null, "status": "provided", "confidence": 0.95, "source_text": "10 x 12 inch", "source": "customer_text"},
    "has_ddp": {"value": false, "unit": null, "status": "not_specified", "confidence": 0.80, "source_text": null, "source": null},
    "has_stevedore": {"value": false, "unit": null, "status": "not_specified", "confidence": 0.80, "source_text": null, "source": null}
  },
  "printing": {
    "printing_sides": {"value": 0, "unit": null, "status": "provided", "confidence": 0.95, "source_text": "No printing", "source": "customer_text"},
    "printing_colors": {"value": 0, "unit": null, "status": "provided", "confidence": 0.95, "source_text": "No printing", "source": "customer_text"},
    "printing_color_names": {"value": [], "unit": null, "status": "inapplicable", "confidence": 1.0, "source_text": null, "source": null}
  },
  "notes": []
}
```

## Deterministic PhysicalBOM

```json
{
  "bom_id": "demo-rule-bom-001",
  "source": "rule_engine",
  "source_spec_id": "demo-spec-001",
  "bag_type": "u_panel",
  "swl_kg": 1250,
  "sf": 5,
  "ext_L": 89,
  "ext_W": 89,
  "ext_H": 114,
  "int_L": 85,
  "int_W": 85,
  "int_H": 110,
  "bag_weight_target_g": 1500,
  "bag_weight_actual_g": 1507.956,
  "computed_total_g": 1507.956,
  "components": [
    {"sr": 1, "canonical_name": "BODY PANEL", "original_name": null, "gsm_area": 160, "gsm_per_m": null, "lami_ul": "UNLAMINATED", "color": "WHITE", "width_cm": 97, "cut_cm": 320, "qty": 1, "weight_g": 496.64, "remark": "ext formula: 2*114+89+10"},
    {"sr": 2, "canonical_name": "SIDE PANEL", "original_name": null, "gsm_area": 160, "gsm_per_m": null, "lami_ul": "UNLAMINATED", "color": "WHITE", "width_cm": 97, "cut_cm": 122, "qty": 2, "weight_g": 378.688, "remark": "ext formula: 114+8"},
    {"sr": 3, "canonical_name": "TOP PANEL", "original_name": null, "gsm_area": 90, "gsm_per_m": null, "lami_ul": "LAMINATED", "color": "WHITE", "width_cm": 102, "cut_cm": 102, "qty": 1, "weight_g": 93.636, "remark": "65+25 LAMI"},
    {"sr": 4, "canonical_name": "FILLING SPOUT", "original_name": null, "gsm_area": 90, "gsm_per_m": null, "lami_ul": "LAMINATED", "color": "WHITE", "width_cm": 55, "cut_cm": 138, "qty": 1, "weight_g": 68.31, "remark": "dia*3.14+12"},
    {"sr": 5, "canonical_name": "DISCHARGE SPOUT", "original_name": null, "gsm_area": 90, "gsm_per_m": null, "lami_ul": "LAMINATED", "color": "WHITE", "width_cm": 80, "cut_cm": 122, "qty": 1, "weight_g": 87.84, "remark": "iris height rounded to approved width"},
    {"sr": 6, "canonical_name": "DS TIE", "original_name": null, "gsm_area": null, "gsm_per_m": 7, "lami_ul": "PP", "color": "WHITE", "width_cm": 1.5, "cut_cm": 148, "qty": 1, "weight_g": 10.36, "remark": "iris tie"},
    {"sr": 7, "canonical_name": "DS TIE", "original_name": null, "gsm_area": null, "gsm_per_m": 7, "lami_ul": "PP", "color": "WHITE", "width_cm": 1.5, "cut_cm": 125, "qty": 1, "weight_g": 8.75, "remark": "DS tie"},
    {"sr": 8, "canonical_name": "FS TIE", "original_name": null, "gsm_area": null, "gsm_per_m": 7, "lami_ul": "PP", "color": "WHITE", "width_cm": 1.5, "cut_cm": 125, "qty": 1, "weight_g": 8.75, "remark": "FS tie"},
    {"sr": 9, "canonical_name": "CORNER LOOP", "original_name": null, "gsm_area": null, "gsm_per_m": 40, "lami_ul": "PP", "color": "WHITE", "width_cm": 5, "cut_cm": 180, "qty": 4, "weight_g": 288, "remark": "LL+SL+60 observed; minimum rule LL+SL+50"},
    {"sr": 10, "canonical_name": "DOC POCKET", "original_name": null, "gsm_area": 70, "gsm_per_m": null, "lami_ul": "LAMINATED", "color": "NATURAL", "width_cm": 25, "cut_cm": 31, "qty": 1, "weight_g": 9.982, "remark": "10x12 inch normalized"},
    {"sr": 11, "canonical_name": "STITCHING", "original_name": null, "gsm_area": null, "gsm_per_m": null, "lami_ul": null, "color": "WHITE", "width_cm": null, "cut_cm": null, "qty": 1, "weight_g": 55, "remark": "0.45*ext_H rounded"},
    {"sr": 12, "canonical_name": "LABEL", "original_name": null, "gsm_area": null, "gsm_per_m": null, "lami_ul": null, "color": null, "width_cm": null, "cut_cm": null, "qty": 1, "weight_g": 2, "remark": "mandatory generated item"}
  ],
  "candidate_optional_components": [],
  "assumptions": [
    {"id": "A001", "field": "loop_color", "assumption": "loop color inherited from fabric color", "basis": "color_default_rule"},
    {"id": "A002", "field": "top_gsm", "assumption": "90 GSM laminated top selected from dominant historical pattern", "basis": "dataset_default"}
  ],
  "rule_hits": [
    {"rule_id": "U_PANEL_MANDATORY_COMPONENTS", "rule_level": "hard_constraint"},
    {"rule_id": "SQ_CORNER_SF5_SWL_1250_MIN_GSM", "rule_level": "hard_constraint"},
    {"rule_id": "U_PANEL_EXTERNAL_GEOMETRY", "rule_level": "hard_constraint"},
    {"rule_id": "CORNER_LOOP_BELT_TABLE", "rule_level": "default_preference"}
  ],
  "constraint_inputs": {
    "design_load_kg": 6250,
    "selected_gsm_basis": "gsm_vs_swl_sf_image_table",
    "static_rule_table_version": "2026-05-26"
  }
}
```

## Top-3 Retrieval Result Format

```json
[
  {
    "retrieval_id": "ret-001",
    "source_file": "01.01.2025 90X90X100CM U+2.xlsx",
    "source_sheet": "01.01.25 8585110cm u+2",
    "record_index": 0,
    "score_total": 0.97,
    "score_breakdown": {"geometric": 0.48, "categorical": 0.39, "semantic": 0.10},
    "why_matched": ["same u_panel bag type", "same 85x85x110 internal size", "same SWL 1250 and SF 5", "same FS/DS/doc pocket pattern"],
    "structured_spec_snapshot": {"bag_type": "u_panel", "int_L": 85, "int_W": 85, "int_H": 110, "swl_kg": 1250, "sf": 5},
    "component_list": [
      {"canonical_name": "BODY PANEL", "gsm_area": 160, "width_cm": 97, "cut_cm": 320, "qty": 1, "weight_g": 496.64},
      {"canonical_name": "SIDE PANEL", "gsm_area": 160, "width_cm": 97, "cut_cm": 122, "qty": 2, "weight_g": 378.688}
    ],
    "bag_weight_target_g": 1500,
    "bag_weight_actual_g": 1506.273,
    "data_warnings": ["historical record lacks LABEL component; generated BOM keeps mandatory LABEL"]
  }
]
```

## LLM Synthesis Input Shape

```json
{
  "normalized_structured_spec": "StructuredSpec",
  "deterministic_bom": "PhysicalBOM",
  "retrieved_boms": ["RetrievedBOM", "RetrievedBOM", "RetrievedBOM"],
  "rule_table_summary": {
    "hard_constraints": ["allowed components only", "approved fabric widths only", "GSM >= threshold", "generated weights must match formulas"],
    "allowed_optional_decisions": ["include optional components only when customer or retrieval supports them"]
  },
  "output_schema": "PhysicalBOM plus rationale fields",
  "instruction": "Output JSON only."
}
```

## LLM Synthesis Output Shape

```json
{
  "bom": "PhysicalBOM",
  "decision_rationale": [
    "Used deterministic U-panel geometry because it matches the exact historical record.",
    "Kept LABEL because generated BOM mandatory matrix requires it even when the historical source omitted it."
  ],
  "differences_from_rule_engine": [],
  "borrowed_patterns_from_retrieval": [
    "Used 90 GSM laminated top/FS/DS pattern.",
    "Used 70 GSM laminated doc pocket pattern."
  ],
  "open_uncertainties": [
    "Customer said outer dimensions are approximate; final approval should confirm external size tolerance."
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
      "code": "TARGET_ACTUAL_WEIGHT_GAP_MINOR",
      "path": "bag_weight_actual_g",
      "message": "Generated actual differs from target by less than 10 percent.",
      "actual_value": 1507.956,
      "reference_value": 1500
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
  "audit_trail_path": "runs/demo-query-001/audit.json",
  "csv_path": "runs/demo-query-001/bom.csv",
  "xlsx_path": "runs/demo-query-001/bom.xlsx",
  "summary": {
    "bag_type": "u_panel",
    "bag_weight_target_g": 1500,
    "bag_weight_actual_g": 1507.956,
    "warnings_count": 1,
    "retrieved_examples_used": 3
  },
  "provenance": {
    "rule_table_versions": ["hard_constraints:2026-05-26", "defaults:2026-05-26", "heuristics:2026-05-26"],
    "retrieved_sources": ["01.01.2025 90X90X100CM U+2.xlsx::01.01.25 8585110cm u+2"],
    "model_name": null
  }
}
```
