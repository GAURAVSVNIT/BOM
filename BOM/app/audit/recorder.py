from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.contracts.models import AuditTrail, CustomerQueryRaw, PhysicalBOM, RetrievedBOM, StructuredSpec, ValidationReport


def create_audit_trail(
    raw_query: CustomerQueryRaw,
    structured_spec: StructuredSpec,
    normalization_changes: list[dict],
    rule_engine_bom: PhysicalBOM | None = None,
    validation_reports: list[ValidationReport] | None = None,
    retrieved_boms: list[RetrievedBOM] | None = None,
    final_bom: PhysicalBOM | None = None,
    final_pass_fail: str | None = None,
) -> AuditTrail:
    return AuditTrail(
        run_id=f"run-{uuid4()}",
        raw_query=raw_query.model_dump(mode="json"),
        structured_spec=structured_spec.model_dump(mode="json"),
        normalization_changes=normalization_changes,
        rule_engine_bom=rule_engine_bom.model_dump(mode="json") if rule_engine_bom else None,
        rule_hits=[h.model_dump(mode="json") for h in rule_engine_bom.rule_hits] if rule_engine_bom else [],
        retrieved_boms=[r.model_dump(mode="json") for r in (retrieved_boms or [])],
        validation_reports=[v.model_dump(mode="json") for v in (validation_reports or [])],
        final_bom=final_bom.model_dump(mode="json") if final_bom else None,
        final_pass_fail=final_pass_fail,
        created_at=datetime.now(),
    )


def write_audit(audit: AuditTrail, run_dir: Path) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "audit.json"
    path.write_text(json.dumps(audit.model_dump(mode="json"), indent=2), encoding="utf-8")
    return path
