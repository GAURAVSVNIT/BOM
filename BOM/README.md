# BOM Generator System

Sprint 1 status: contracts and static rule tables only.

This folder is intentionally documentation-first. Do not add model calls,
embeddings, API routes, or CSV/XLSX generation until these interfaces are
reviewed and frozen.

## Contents

- `docs/01_contracts.md`: canonical object contracts for the full pipeline.
- `docs/02_rule_tables.md`: static knowledge tables and rule priority system.
- `docs/03_paper_example.md`: one end-to-end paper run through the architecture.
- `rules/hard_constraints.json`: rejectable constraints only.
- `rules/defaults.json`: deterministic defaults only.
- `rules/heuristics.json`: fallback logic, warnings, and ML advisory settings.
- `data/processed/`: prepared retrieval corpus and frequency stats.
- `app/`: executable pipeline modules.

## Source Material Used

- `new_bom_training_corrected.csv`: 559 corrected records with normalized numeric
  fields and feature flags.
- `bom_extracted_dataset.json`: 559 structured BOM records with component lists.
- `bom_system/bom_engine.py`: existing prototype formulas and helper logic.
- `BAG_TYPE_-_UPANEL..pdf`: U-panel component formulas.
- `DocScanner 13 Apr 2026 9-35...pm.pdf` scan pages: handwritten U-panel work
  order and formula notes.
- `U_Panel_Bag_=_Upanel_Bug.pdf`: bag type taxonomy.
- Supplied GSM and belt GPM images.

## Non-Negotiable Boundaries

- Internal units are `cm`, `g`, and `kg`; tape widths may also be represented in
  `mm` when that is the customer/source unit.
- `StructuredSpec` contains customer intent only, not engineered decisions.
- `PhysicalBOM` is the only generated BOM shape.
- Validation is the authority. Retrieval and LLM synthesis cannot override hard
  constraints.
- The deterministic rule engine must produce a legal BOM without retrieval or an
  LLM.
- Costing is intentionally excluded. The system currently models physical BOM
  chemistry/physics: components, GSM/GPM, lamination, dimensions, weights,
  validation, retrieval evidence, and output packaging.

## Current Executable Scope

- Implemented: U-panel normalization, deterministic rule engine, validation,
  hybrid retrieval, retrieval advisory, audit, CSV/XLSX output, and U-panel
  regression tests.
- Not yet implemented: production-grade geometry modules for circular,
  four-panel, baffle, single-loop, and two-loop bags. Their contracts and
  compatibility rules exist so they can be added separately without changing the
  shared BOM shape.
