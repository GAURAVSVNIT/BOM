from __future__ import annotations

import csv
import json
from pathlib import Path
from uuid import uuid4

from openpyxl import Workbook

from app.audit import write_audit
from app.contracts.models import AuditTrail, FinalBOMPackage, PhysicalBOM, RetrievedBOM, ValidationReport


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _bom_rows(bom: PhysicalBOM) -> list[dict]:
    rows = []
    for comp in bom.components:
        rows.append({
            "SR": comp.sr,
            "COMPONENT": comp.canonical_name,
            "GSM": comp.gsm_area,
            "GPM": comp.gsm_per_m,
            "LAMI_UL": comp.lami_ul,
            "COLOR": comp.color,
            "WIDTH_CM": comp.width_cm,
            "CUT_CM": comp.cut_cm,
            "QTY": comp.qty,
            "WEIGHT_G": comp.weight_g,
            "REMARK": comp.remark,
            "RULE_SOURCE": comp.source,
            "RETRIEVAL_SOURCE": "",
        })
    return rows


def _write_csv(bom: PhysicalBOM, path: Path) -> None:
    rows = _bom_rows(bom)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _append_sheet(wb: Workbook, title: str, rows: list[dict]) -> None:
    ws = wb.create_sheet(title)
    if not rows:
        ws.append(["EMPTY"])
        return
    headers = list(rows[0].keys())
    ws.append(headers)
    for row in rows:
        ws.append([row.get(h) for h in headers])


def _write_xlsx(bom: PhysicalBOM, validation: ValidationReport, audit: AuditTrail, retrieved: list[RetrievedBOM], path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "BOM"
    rows = _bom_rows(bom)
    ws.append(list(rows[0].keys()))
    for row in rows:
        ws.append([row.get(h) for h in rows[0].keys()])

    _append_sheet(wb, "Summary", [{
        "bag_type": bom.bag_type,
        "swl_kg": bom.swl_kg,
        "sf": bom.sf,
        "target_g": bom.bag_weight_target_g,
        "actual_g": bom.bag_weight_actual_g,
        "computed_total_g": bom.computed_total_g,
    }])
    _append_sheet(wb, "Validation", [i.model_dump(mode="json") for i in validation.hard_failures + validation.soft_warnings])
    _append_sheet(wb, "Audit", [{"run_id": audit.run_id, "final_pass_fail": audit.final_pass_fail, "retry_count": audit.retry_count}])
    _append_sheet(wb, "Retrieved_Examples", [
        {
            "source_file": r.source_file,
            "source_sheet": r.source_sheet,
            "score_total": r.score_total,
            "actual_g": r.bag_weight_actual_g,
            "why": "; ".join(r.why_matched),
        }
        for r in retrieved
    ])
    wb.save(path)


def write_final_package(
    bom: PhysicalBOM,
    validation: ValidationReport,
    audit: AuditTrail,
    retrieved: list[RetrievedBOM] | None = None,
    runs_root: Path | None = None,
) -> FinalBOMPackage:
    runs_root = runs_root or PROJECT_ROOT / "runs"
    run_dir = runs_root / audit.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    csv_path = run_dir / "bom.csv"
    xlsx_path = run_dir / "bom.xlsx"
    summary_path = run_dir / "summary.json"
    provenance_path = run_dir / "provenance.json"
    audit_path = write_audit(audit, run_dir)
    _write_csv(bom, csv_path)
    _write_xlsx(bom, validation, audit, retrieved or [], xlsx_path)

    summary = {
        "bag_type": bom.bag_type,
        "bag_weight_target_g": bom.bag_weight_target_g,
        "bag_weight_actual_g": bom.bag_weight_actual_g,
        "warnings_count": len(validation.soft_warnings),
        "retrieved_examples_used": len(retrieved or []),
    }
    provenance = {
        "rule_table_versions": [
            f"hard_constraints:{bom.constraint_inputs.get('static_rule_table_version')}",
            "defaults:2026-05-26",
            "heuristics:2026-05-26",
        ],
        "retrieved_sources": [f"{r.source_file}::{r.source_sheet}" for r in (retrieved or [])],
        "model_name": None,
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    provenance_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    return FinalBOMPackage(
        package_id=f"pkg-{uuid4()}",
        final_bom=bom,
        validation_report=validation,
        audit_trail_path=str(audit_path),
        csv_path=str(csv_path),
        xlsx_path=str(xlsx_path),
        summary=summary,
        provenance=provenance,
    )
