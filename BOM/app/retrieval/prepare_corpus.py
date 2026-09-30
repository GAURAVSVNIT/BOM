from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def prepare_historical_corpus(
    dataset_path: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Path]:
    dataset_path = dataset_path or PROJECT_ROOT / "bom_extracted_dataset.json"
    output_dir = output_dir or PROJECT_ROOT / "bom_generator_system" / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)
    records = json.loads(dataset_path.read_text(encoding="utf-8"))

    numeric_rows: list[dict[str, Any]] = []
    text_rows: list[dict[str, Any]] = []
    component_counter: Counter[str] = Counter()
    width_counter: Counter[float] = Counter()
    gsm_by_family: dict[str, Counter[float]] = defaultdict(Counter)
    rare_flags: Counter[str] = Counter()

    for idx, rec in enumerate(records):
        numeric_rows.append({
            "record_index": idx,
            "source_file": rec.get("source_file"),
            "source_sheet": rec.get("source_sheet"),
            "bag_type": rec.get("bag_type"),
            "int_L": rec.get("int_L"),
            "int_W": rec.get("int_W"),
            "int_H": rec.get("int_H"),
            "ext_L": rec.get("ext_L"),
            "ext_W": rec.get("ext_W"),
            "ext_H": rec.get("ext_H"),
            "swl_kg": rec.get("swl_kg"),
            "sf": rec.get("sf"),
            "top_type": rec.get("top_type"),
            "has_baffle": rec.get("has_baffle"),
            "has_liner": rec.get("has_liner"),
            "has_fs_spout": rec.get("has_fs_spout"),
            "has_ds_spout": rec.get("has_ds_spout"),
            "has_doc_pocket": rec.get("has_doc_pocket"),
            "has_ddp": rec.get("has_ddp"),
            "has_stevedore": rec.get("has_stevedore"),
            "loop_qty": rec.get("loop_qty"),
            "loop_width_mm": rec.get("loop_width_mm"),
            "bag_weight_target_g": rec.get("bag_weight_target_g"),
            "bag_weight_actual_g": rec.get("bag_weight_actual_g"),
        })
        component_names = []
        for comp in rec.get("components", []):
            name = comp.get("canonical_name")
            if name:
                component_counter[name] += 1
                component_names.append(name)
            if comp.get("width_cm") is not None:
                width_counter[float(comp["width_cm"])] += 1
            if comp.get("gsm_area") is not None and rec.get("bag_type"):
                gsm_by_family[rec["bag_type"]][float(comp["gsm_area"])] += 1
        combo = "|".join([
            str(rec.get("bag_type")),
            str(rec.get("top_type")),
            "fs" if rec.get("has_fs_spout") else "no_fs",
            "ds" if rec.get("has_ds_spout") else "no_ds",
            "liner" if rec.get("has_liner") else "no_liner",
            "ddp" if rec.get("has_ddp") else "no_ddp",
        ])
        rare_flags[combo] += 1
        text_rows.append({
            "record_index": idx,
            "source_file": rec.get("source_file"),
            "source_sheet": rec.get("source_sheet"),
            "text": " ".join([
                str(rec.get("instruction") or ""),
                str(rec.get("bag_type") or ""),
                str(rec.get("top_type") or ""),
                " ".join(component_names),
            ]),
        })

    numeric_path = output_dir / "retrieval_numeric.csv"
    text_path = output_dir / "retrieval_text.jsonl"
    component_stats_path = output_dir / "component_stats.json"
    width_frequency_path = output_dir / "width_frequency.json"
    gsm_frequency_path = output_dir / "gsm_frequency_by_family.json"
    rare_path = output_dir / "rare_combination_flags.json"

    pd.DataFrame(numeric_rows).to_csv(numeric_path, index=False)
    with text_path.open("w", encoding="utf-8") as handle:
        for row in text_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    component_stats_path.write_text(json.dumps(component_counter.most_common(), indent=2), encoding="utf-8")
    width_frequency_path.write_text(json.dumps(width_counter.most_common(), indent=2), encoding="utf-8")
    gsm_frequency_path.write_text(json.dumps({k: v.most_common() for k, v in gsm_by_family.items()}, indent=2), encoding="utf-8")
    rare_path.write_text(json.dumps([{"combo": k, "count": v} for k, v in rare_flags.items() if v <= 2], indent=2), encoding="utf-8")
    return {
        "numeric": numeric_path,
        "text": text_path,
        "component_stats": component_stats_path,
        "width_frequency": width_frequency_path,
        "gsm_frequency_by_family": gsm_frequency_path,
        "rare_combination_flags": rare_path,
    }


if __name__ == "__main__":
    paths = prepare_historical_corpus()
    for name, path in paths.items():
        print(f"{name}: {path}")
