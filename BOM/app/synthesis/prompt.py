from __future__ import annotations

import json
from typing import Any

from app.contracts.models import PhysicalBOM, RetrievedBOM, StructuredSpec
from app.rules.loader import RuleBook, load_rulebook


def build_synthesis_prompt(
    spec: StructuredSpec,
    deterministic_bom: PhysicalBOM,
    retrieved_boms: list[RetrievedBOM],
    rules: RuleBook | None = None,
    validation_error_context: dict[str, Any] | None = None,
) -> str:
    rules = rules or load_rulebook()
    payload = {
        "role": "You are a FIBC BOM engineer.",
        "forbidden": [
            "Do not invent loom widths.",
            "Do not choose GSM below minimum structural threshold.",
            "Do not add forbidden component names.",
            "Do not omit mandatory components.",
            "Do not output prose outside JSON.",
            "Do not add optional components unless customer spec or retrieval supports them.",
        ],
        "hard_constraints_summary": {
            "canonical_components": rules.hard["canonical_components"],
            "approved_loom_widths_cm": rules.hard["approved_loom_widths_cm"],
            "minimum_structural_gsm_rules": rules.hard["minimum_structural_gsm_rules"],
            "component_policy": rules.hard["component_policy"],
            "mandatory_by_bag_type": rules.hard["mandatory_by_bag_type"],
            "mandatory_by_top_type": rules.hard["mandatory_by_top_type"],
            "mandatory_by_bottom_type": rules.hard["mandatory_by_bottom_type"],
            "mandatory_by_accessory_flag": rules.hard["mandatory_by_accessory_flag"],
            "mandatory_by_closure_type": rules.hard["mandatory_by_closure_type"],
        },
        "normalized_structured_spec": spec.model_dump(mode="json"),
        "deterministic_bom": deterministic_bom.model_dump(mode="json"),
        "retrieved_boms": [r.model_dump(mode="json") for r in retrieved_boms],
        "validation_error_context": validation_error_context or {},
        "task": "Return JSON with keys: bom, decision_rationale, differences_from_rule_engine, borrowed_patterns_from_retrieval, open_uncertainties.",
    }
    return json.dumps(payload, ensure_ascii=False)
