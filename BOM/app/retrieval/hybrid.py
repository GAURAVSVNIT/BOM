from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.contracts.models import PhysicalBOM, RetrievedBOM, StructuredSpec


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _value(obj: Any, default: Any = None) -> Any:
    return obj.value if getattr(obj, "value", None) is not None else default


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


@dataclass
class RetrievalAdvisory:
    suggested_optional_components: list[str]
    candidate_alternative_gsms: dict[str, list[float]]
    candidate_loop_configs: list[dict[str, Any]]
    weight_delta_analysis: list[dict[str, Any]]
    disagreement_report: list[str]


class HybridRetriever:
    def __init__(self, dataset_path: str | Path | None = None) -> None:
        self.dataset_path = Path(dataset_path) if dataset_path else PROJECT_ROOT / "bom_extracted_dataset.json"
        self.records = json.loads(self.dataset_path.read_text(encoding="utf-8"))
        self.texts = [self._record_text(r) for r in self.records]
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
        self.matrix = self.vectorizer.fit_transform(self.texts)

    def _record_text(self, record: dict[str, Any]) -> str:
        components = " ".join(c.get("canonical_name", "") for c in record.get("components", []))
        flags = " ".join(
            key for key in ["has_liner", "has_baffle", "has_ds_spout", "has_fs_spout", "has_ddp", "has_doc_pocket"]
            if record.get(key)
        )
        return " ".join([
            str(record.get("instruction") or ""),
            str(record.get("bag_type") or ""),
            str(record.get("top_type") or ""),
            str(record.get("bottom_type") or ""),
            flags,
            components,
        ])

    def _query_text(self, spec: StructuredSpec) -> str:
        return " ".join([
            str(_value(spec.bag_type, "")),
            str(_value(spec.top_type, "")),
            str(_value(spec.bottom_type, "")),
            "fs_spout" if _value(spec.accessories.has_fs_spout, False) else "",
            "ds_spout" if _value(spec.accessories.has_ds_spout, False) else "",
            "liner" if _value(spec.accessories.has_liner, False) else "",
            "baffle" if _value(spec.accessories.has_baffle, False) else "",
            "ddp" if _value(spec.accessories.has_ddp, False) else "",
            "doc pocket" if _value(spec.accessories.has_doc_pocket, False) else "",
            " ".join(spec.notes),
        ])

    def _geometric_score(self, spec: StructuredSpec, record: dict[str, Any]) -> float:
        pairs = [
            (_value(spec.dimensions.int_L), record.get("int_L")),
            (_value(spec.dimensions.int_W), record.get("int_W")),
            (_value(spec.dimensions.int_H), record.get("int_H")),
            (_value(spec.dimensions.ext_L), record.get("ext_L")),
            (_value(spec.dimensions.ext_W), record.get("ext_W")),
            (_value(spec.dimensions.ext_H), record.get("ext_H")),
            (_value(spec.swl_kg), record.get("swl_kg")),
            (_value(spec.sf), record.get("sf")),
        ]
        scores = []
        for a, b in pairs:
            if a is None or b is None:
                continue
            denom = max(abs(_num(a)), abs(_num(b)), 1.0)
            scores.append(max(0.0, 1.0 - abs(_num(a) - _num(b)) / denom))
        if _value(spec.bag_weight_target_g) and record.get("bag_weight_target_g"):
            a = _num(_value(spec.bag_weight_target_g))
            b = _num(record.get("bag_weight_target_g"))
            scores.append(max(0.0, 1.0 - abs(a - b) / max(a, b, 1.0)))
        return float(np.mean(scores)) if scores else 0.0

    def _categorical_score(self, spec: StructuredSpec, record: dict[str, Any]) -> tuple[float, list[str]]:
        checks = [
            ("bag_type", _value(spec.bag_type), record.get("bag_type")),
            ("top_type", _value(spec.top_type), record.get("top_type")),
            ("has_baffle", _value(spec.accessories.has_baffle, False), record.get("has_baffle")),
            ("has_liner", _value(spec.accessories.has_liner, False), record.get("has_liner")),
            ("has_fs_spout", _value(spec.accessories.has_fs_spout, False), record.get("has_fs_spout")),
            ("has_ds_spout", _value(spec.accessories.has_ds_spout, False), record.get("has_ds_spout")),
            ("has_ddp", _value(spec.accessories.has_ddp, False), record.get("has_ddp")),
            ("has_doc_pocket", _value(spec.accessories.has_doc_pocket, False), record.get("has_doc_pocket")),
        ]
        hits = []
        total = 0
        for name, a, b in checks:
            if a is None:
                continue
            total += 1
            if a == b:
                hits.append(name)
        return (len(hits) / total if total else 0.0), [f"matched {h}" for h in hits]

    def retrieve(self, spec: StructuredSpec, top_k: int = 3) -> list[RetrievedBOM]:
        q_vec = self.vectorizer.transform([self._query_text(spec)])
        semantic_scores = cosine_similarity(q_vec, self.matrix)[0]
        results = []
        for idx, record in enumerate(self.records):
            if _value(spec.bag_type) and record.get("bag_type") != _value(spec.bag_type):
                bag_penalty = 0.35
            else:
                bag_penalty = 1.0
            geo = self._geometric_score(spec, record)
            cat, why = self._categorical_score(spec, record)
            sem = float(semantic_scores[idx])
            total = bag_penalty * (0.5 * geo + 0.35 * cat + 0.15 * sem)
            if record.get("bag_type") == _value(spec.bag_type):
                why.insert(0, f"same bag_type {record.get('bag_type')}")
            results.append((total, geo, cat, sem, why, idx, record))
        results.sort(key=lambda item: item[0], reverse=True)
        retrieved: list[RetrievedBOM] = []
        for total, geo, cat, sem, why, idx, record in results[:top_k]:
            retrieved.append(RetrievedBOM(
                retrieval_id=f"ret-{uuid4()}",
                source_file=record.get("source_file") or "",
                source_sheet=record.get("source_sheet") or "",
                record_index=idx,
                score_total=round(float(total), 4),
                score_breakdown={"geometric": round(float(geo), 4), "categorical": round(float(cat), 4), "semantic": round(float(sem), 4)},
                why_matched=why[:8],
                structured_spec_snapshot={
                    "bag_type": record.get("bag_type"),
                    "int_L": record.get("int_L"),
                    "int_W": record.get("int_W"),
                    "int_H": record.get("int_H"),
                    "swl_kg": record.get("swl_kg"),
                    "sf": record.get("sf"),
                    "top_type": record.get("top_type"),
                    "has_fs_spout": record.get("has_fs_spout"),
                    "has_ds_spout": record.get("has_ds_spout"),
                    "has_doc_pocket": record.get("has_doc_pocket"),
                    "has_ddp": record.get("has_ddp"),
                },
                component_list=record.get("components", []),
                bag_weight_target_g=record.get("bag_weight_target_g"),
                bag_weight_actual_g=record.get("bag_weight_actual_g"),
                data_warnings=[record["data_warning"]] if record.get("data_warning") else [],
            ))
        return retrieved


def build_retrieval_advisory(deterministic_bom: PhysicalBOM, retrieved: list[RetrievedBOM]) -> RetrievalAdvisory:
    det_names = {c.canonical_name for c in deterministic_bom.components}
    optional_counts: dict[str, int] = {}
    gsm_candidates: dict[str, set[float]] = {}
    loop_configs: list[dict[str, Any]] = []
    deltas: list[dict[str, Any]] = []
    disagreements: list[str] = []

    for item in retrieved:
        names = {c.get("canonical_name") for c in item.component_list}
        for name in names - det_names:
            if name:
                optional_counts[name] = optional_counts.get(name, 0) + 1
        for comp in item.component_list:
            name = comp.get("canonical_name")
            if comp.get("gsm_area") is not None:
                gsm_candidates.setdefault(name, set()).add(float(comp["gsm_area"]))
            if name == "CORNER LOOP":
                loop_configs.append({
                    "source_file": item.source_file,
                    "gsm_per_m": comp.get("gsm_per_m"),
                    "width_cm": comp.get("width_cm"),
                    "cut_cm": comp.get("cut_cm"),
                    "qty": comp.get("qty"),
                })
        if item.bag_weight_actual_g is not None:
            deltas.append({
                "source_file": item.source_file,
                "retrieved_actual_g": item.bag_weight_actual_g,
                "deterministic_actual_g": deterministic_bom.bag_weight_actual_g,
                "delta_g": round(item.bag_weight_actual_g - deterministic_bom.bag_weight_actual_g, 3),
            })
        if item.structured_spec_snapshot.get("bag_type") != deterministic_bom.bag_type:
            disagreements.append(f"{item.source_file}: bag type differs")

    suggested = sorted(name for name, count in optional_counts.items() if count >= max(1, len(retrieved) // 2))
    return RetrievalAdvisory(
        suggested_optional_components=suggested,
        candidate_alternative_gsms={k: sorted(v) for k, v in gsm_candidates.items()},
        candidate_loop_configs=loop_configs[:5],
        weight_delta_analysis=deltas,
        disagreement_report=disagreements,
    )
