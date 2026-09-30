# Anjani FIBC BOM Generator V2

This folder is the clean build for the production BOM generator.

The current `bom_system/` folder remains a prototype/reference. This V2 project
starts with frozen interfaces and rule tables before adding Sarvam extraction,
retrieval, or LLM synthesis.

## Build Order

1. Canonical schema
2. Validation tables
3. Rule engine
4. Retrieval
5. Audit trail
6. LLM synthesis
7. Retry loop
8. CSV/XLSX output
9. Offline evaluation set

## Sprint 1 Deliverables

- `docs/01_system_contract.md`
- `docs/02_rule_tables.md`
- `docs/03_architecture_and_build_order.md`
- `docs/04_end_to_end_paper_example.md`
- `rules/static_rule_tables.json`

## Non-Negotiable Design Rules

- Internal canonical units are centimeters and grams.
- `bag_weight_target_g` and `bag_weight_actual_g` are separate forever.
- Missing SWL/SF is valid and must be represented as `not_specified`.
- Validation is the authority, not the model.
- Retrieval assists; it never overrides hard constraints.
- The deterministic rule engine must work without LLM or retrieval.
- Every decision must be auditable.

