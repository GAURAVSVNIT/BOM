from __future__ import annotations

from app.audit import create_audit_trail
from app.contracts.models import FinalBOMPackage
from app.normalization.extractor import raw_query_from_text, normalize_customer_query
from app.output import write_final_package
from app.retrieval.hybrid import HybridRetriever, build_retrieval_advisory
from app.rules import generate_u_panel_bom
from app.synthesis import synthesize_with_retry
from app.validation import validate_bom


def run_pipeline(query_text: str, with_retrieval: bool = True, llm=None) -> FinalBOMPackage:
    raw = raw_query_from_text(query_text)
    normalized = normalize_customer_query(raw)
    spec = normalized.structured_spec
    if spec.bag_type.value != "u_panel":
        raise ValueError("Only u_panel deterministic generation is implemented in this sprint.")

    bom = generate_u_panel_bom(spec)
    validation = validate_bom(bom)
    retrieved = []
    if with_retrieval and not validation.hard_failures:
        retriever = HybridRetriever()
        retrieved = retriever.retrieve(spec, top_k=3)
        advisory = build_retrieval_advisory(bom, retrieved)
        normalized.changes.append({"field": "retrieval_advisory", "value": advisory.__dict__, "basis": "hybrid_retrieval"})
    synthesis = synthesize_with_retry(spec, bom, retrieved, llm=llm)
    final_bom = synthesis.final_bom
    final_validation = synthesis.validation_report

    audit = create_audit_trail(
        raw_query=raw,
        structured_spec=spec,
        normalization_changes=normalized.changes,
        rule_engine_bom=bom,
        validation_reports=[validation],
        retrieved_boms=retrieved,
        final_bom=final_bom,
        final_pass_fail="pass_with_warnings" if final_validation.soft_warnings else "pass",
    )
    audit.llm_prompt_version = synthesis.prompt_version
    audit.llm_raw_output = {"outputs": synthesis.llm_raw_outputs, "used_fallback": synthesis.used_fallback}
    audit.retry_count = synthesis.retry_count
    return write_final_package(final_bom, final_validation, audit, retrieved)
