from __future__ import annotations

import csv
import io

HEADER = ["SR", "COMPONENT", "GSM", "LAMI/UL", "COLOR", "WIDTH_CM", "CUT_CM", "QTY", "WEIGHT_G", "REMARK"]


class BomCsvError(ValueError):
    pass


def parse_bom_csv(text: str) -> tuple[list[dict[str, str]], float | None]:
    """Parse the flat BOM CSV format used by bom_finetuning_dataset*.jsonl's `output` field.

    Returns (component_rows, grand_total_g). Raises BomCsvError on structural problems
    so callers can treat a malformed generation as a hard failure, not a silent skip.
    """
    rows = [r for r in csv.reader(io.StringIO(text.strip())) if r]
    if not rows:
        raise BomCsvError("empty output")

    header = [c.strip() for c in rows[0]]
    if header != HEADER:
        raise BomCsvError(f"unexpected header: {header!r}, expected {HEADER!r}")

    components: list[dict[str, str]] = []
    grand_total: float | None = None
    for row in rows[1:]:
        joined = ",".join(row).strip()
        if not joined:
            continue
        if joined.upper().startswith("GRAND TOTAL"):
            digits = "".join(ch for ch in joined if ch.isdigit() or ch == ".")
            grand_total = float(digits) if digits else None
            continue
        padded = row + [""] * (len(HEADER) - len(row)) if len(row) < len(HEADER) else row[: len(HEADER)]
        components.append(dict(zip(HEADER, (c.strip() for c in padded))))

    if grand_total is None:
        raise BomCsvError("no GRAND TOTAL row found")
    return components, grand_total


def component_weight_sum(components: list[dict[str, str]]) -> float:
    total = 0.0
    for comp in components:
        raw = comp.get("WEIGHT_G", "")
        try:
            total += float(raw)
        except ValueError:
            continue
    return round(total, 3)
