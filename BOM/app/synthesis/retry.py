from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable

from pydantic import ValidationError

from app.contracts.models import PhysicalBOM, RetrievedBOM, StructuredSpec, ValidationReport
from app.rules.loader import RuleBook, load_rulebook
from app.synthesis.prompt import build_synthesis_prompt
from app.validation import validate_bom


LLMCallable = Callable[[str], str]


@dataclass
class SynthesisResult:
    final_bom: PhysicalBOM
    validation_report: ValidationReport
    retry_count: int
    llm_raw_outputs: list[dict]
    prompt_version: str
    used_fallback: bool


def synthesize_with_retry(
    spec: StructuredSpec,
    deterministic_bom: PhysicalBOM,
    retrieved_boms: list[RetrievedBOM],
    llm: LLMCallable | None = None,
    rules: RuleBook | None = None,
    max_retries: int = 2,
) -> SynthesisResult:
    rules = rules or load_rulebook()
    deterministic_report = validate_bom(deterministic_bom, rules=rules)
    if llm is None or deterministic_report.hard_failures:
        return SynthesisResult(
            final_bom=deterministic_bom,
            validation_report=deterministic_report,
            retry_count=0,
            llm_raw_outputs=[],
            prompt_version="synthesis_v1",
            used_fallback=True,
        )

    error_context = {}
    raw_outputs: list[dict] = []
    last_report = deterministic_report
    for retry in range(max_retries + 1):
        prompt = build_synthesis_prompt(spec, deterministic_bom, retrieved_boms, rules, error_context)
        try:
            raw_text = llm(prompt)
            parsed = json.loads(raw_text)
            raw_outputs.append(parsed)
            candidate = PhysicalBOM.model_validate(parsed["bom"])
        except (json.JSONDecodeError, KeyError, ValidationError) as exc:
            error_context = {"schema_error": str(exc), "instruction": "Fix JSON/schema only."}
            continue
        report = validate_bom(candidate, rules=rules)
        last_report = report
        if not report.hard_failures:
            return SynthesisResult(
                final_bom=candidate,
                validation_report=report,
                retry_count=retry,
                llm_raw_outputs=raw_outputs,
                prompt_version="synthesis_v1",
                used_fallback=False,
            )
        error_context = report.error_context_for_llm

    return SynthesisResult(
        final_bom=deterministic_bom,
        validation_report=last_report if last_report.hard_failures else deterministic_report,
        retry_count=max_retries,
        llm_raw_outputs=raw_outputs,
        prompt_version="synthesis_v1",
        used_fallback=True,
    )
