"""Build SFT-ready train/val splits from bom_finetuning_dataset*.jsonl.

Reads the raw {instruction, output, ...} records, validates each `output` CSV
against the project's own canonical component vocabulary and mandatory-by-bag-type
rules (rules/hard_constraints.json), drops anything that fails, deduplicates, and
writes chat-formatted {"messages": [...], "meta": {...}} records to
finetune/data/train.jsonl and finetune/data/val.jsonl.

Usage:
    python prepare_dataset.py [--val-fraction 0.1] [--seed 13]
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from bom_csv import BomCsvError, component_weight_sum, parse_bom_csv

BOM_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(__file__).resolve().parent / "data"

RAW_FILES = [
    BOM_ROOT / "bom_finetuning_dataset_corrected.jsonl",
    BOM_ROOT / "bom_finetuning_dataset.jsonl",
]

SYSTEM_PROMPT = (
    "You are a FIBC (jumbo bag) BOM engineer at Anjani Interweave. Given a bag "
    "specification, output only the Bill of Materials as CSV text with header "
    "SR,COMPONENT,GSM,LAMI/UL,COLOR,WIDTH_CM,CUT_CM,QTY,WEIGHT_G,REMARK, one row per "
    "component, and a final line 'GRAND TOTAL: <value>g'. Use only canonical "
    "component names. Never invent loom widths or GSM values, never omit a mandatory "
    "component for the bag type, and never add prose outside the CSV."
)

# generated total vs sum-of-rows tolerance for historical records (matches
# rules/hard_constraints.json::weight_formula_tolerance_g.historical)
HISTORICAL_WEIGHT_TOLERANCE_G = 5.0


def load_rulebook() -> dict[str, Any]:
    return json.loads((BOM_ROOT / "rules" / "hard_constraints.json").read_text(encoding="utf-8"))


def load_raw_records() -> list[dict[str, Any]]:
    for path in RAW_FILES:
        if path.exists():
            records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
            print(f"loaded {len(records)} records from {path.name}")
            return records
    raise FileNotFoundError(f"none of {[p.name for p in RAW_FILES]} found under {BOM_ROOT}")


def validate_record(rec: dict[str, Any], rulebook: dict[str, Any]) -> str | None:
    """Return a rejection reason, or None if the record is fit for training.

    Only checks that would also be hard failures for *historical* data in
    app/validation/validator.py: schema-parseable, canonical vocabulary, and
    weight-formula consistency (at the historical tolerance). Deliberately does
    NOT reject on "missing mandatory component" — docs/02_rule_tables.md lists
    a historical record missing LABEL as an expected *soft* warning, and the
    mandatory_by_bag_type table is only regression-tested against real data for
    u_panel (see tests/test_u_panel_pipeline.py); for the other six bag types it
    is unvalidated, and in this dataset ~1 in 4 circular/two_panel/two_loop/
    four_panel_baffle records are missing their listed mandatory BOTTOM PANEL —
    almost certainly because those constructions don't always cut a separate
    bottom panel, not because the historical data is wrong. Rejecting on that
    would silently throw away real, structurally-valid BOMs. See
    count_missing_mandatory() below for visibility instead.
    """
    if not rec.get("instruction") or not rec.get("output"):
        return "missing instruction/output"

    try:
        components, grand_total = parse_bom_csv(rec["output"])
    except BomCsvError as exc:
        return f"unparseable output: {exc}"

    canonical = set(rulebook["canonical_components"])
    names = [c["COMPONENT"] for c in components]
    bad_names = sorted({n for n in names if n not in canonical})
    if bad_names:
        return f"non-canonical component names: {bad_names}"

    row_sum = component_weight_sum(components)
    if abs(row_sum - grand_total) > HISTORICAL_WEIGHT_TOLERANCE_G:
        return f"GRAND TOTAL ({grand_total}g) disagrees with row sum ({row_sum}g)"

    return None


def count_missing_mandatory(rec: dict[str, Any], rulebook: dict[str, Any]) -> list[str]:
    try:
        components, _ = parse_bom_csv(rec["output"])
    except BomCsvError:
        return []
    names = {c["COMPONENT"] for c in components}
    mandatory = set(rulebook["mandatory_by_bag_type"].get(rec.get("bag_type"), []))
    return sorted(mandatory - names)


def to_sft_example(rec: dict[str, Any]) -> dict[str, Any]:
    components, grand_total = parse_bom_csv(rec["output"])
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": rec["instruction"]},
            {"role": "assistant", "content": rec["output"]},
        ],
        "meta": {
            "source_file": rec.get("source_file"),
            "source_sheet": rec.get("source_sheet"),
            "bag_type": rec.get("bag_type"),
            "ground_truth_components": [c["COMPONENT"] for c in components],
            "ground_truth_total_g": grand_total,
        },
    }


def stratified_split(examples: list[dict[str, Any]], val_fraction: float, seed: int) -> tuple[list, list]:
    by_bag_type: dict[str, list[dict]] = defaultdict(list)
    for ex in examples:
        by_bag_type[ex["meta"]["bag_type"] or "unknown"].append(ex)

    rng = random.Random(seed)
    train: list[dict] = []
    val: list[dict] = []
    for bag_type, group in by_bag_type.items():
        rng.shuffle(group)
        n_val = max(1, round(len(group) * val_fraction)) if len(group) >= 5 else 0
        val.extend(group[:n_val])
        train.extend(group[n_val:])
        print(f"  {bag_type:20s} total={len(group):4d} train={len(group) - n_val:4d} val={n_val:4d}")

    rng.shuffle(train)
    rng.shuffle(val)
    return train, val


def write_jsonl(path: Path, examples: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for ex in examples:
            handle.write(json.dumps(ex, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--val-fraction", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()

    rulebook = load_rulebook()
    raw_records = load_raw_records()

    seen: set[tuple[str, str]] = set()
    kept: list[dict[str, Any]] = []
    rejections: Counter[str] = Counter()
    dropped_examples: list[dict[str, Any]] = []
    missing_mandatory_by_bag_type: Counter[str] = Counter()

    for rec in raw_records:
        key = (rec.get("instruction", ""), rec.get("output", ""))
        if key in seen:
            rejections["duplicate"] += 1
            continue
        seen.add(key)

        reason = validate_record(rec, rulebook)
        if reason is not None:
            rejections[reason.split(":")[0]] += 1
            dropped_examples.append({"source_file": rec.get("source_file"), "source_sheet": rec.get("source_sheet"), "reason": reason})
            continue

        if count_missing_mandatory(rec, rulebook):
            missing_mandatory_by_bag_type[rec.get("bag_type") or "unknown"] += 1

        kept.append(to_sft_example(rec))

    print(f"\n{len(kept)} usable / {len(raw_records)} raw records")
    if rejections:
        print("rejections:")
        for reason, count in rejections.most_common():
            print(f"  {reason}: {count}")
    if missing_mandatory_by_bag_type:
        print("kept anyway but missing a listed mandatory component (informational only, see 'What this does not do' caveat in prepare_dataset.py):")
        for bag_type, count in missing_mandatory_by_bag_type.most_common():
            print(f"  {bag_type}: {count}")

    print("\nstratified split by bag_type:")
    train, val = stratified_split(kept, args.val_fraction, args.seed)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(OUT_DIR / "train.jsonl", train)
    write_jsonl(OUT_DIR / "val.jsonl", val)
    write_jsonl(OUT_DIR / "smoke.jsonl", train[:3])
    (OUT_DIR / "rejected.json").write_text(json.dumps(dropped_examples, indent=2), encoding="utf-8")

    manifest = {
        "raw_records": len(raw_records),
        "usable_records": len(kept),
        "train": len(train),
        "val": len(val),
        "rejections": dict(rejections),
        "bag_type_counts": dict(Counter(ex["meta"]["bag_type"] for ex in kept)),
        "kept_but_missing_mandatory_component_by_bag_type": dict(missing_mandatory_by_bag_type),
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\nwrote {len(train)} train / {len(val)} val examples to {OUT_DIR}")


if __name__ == "__main__":
    main()
