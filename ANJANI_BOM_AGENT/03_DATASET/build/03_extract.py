# -*- coding: utf-8 -*-
"""03_extract.py — parse every BOM sheet in every unique workbook."""
import os, sys, json, collections, warnings, time
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xl_read import read_workbook
from bom_parse import parse_sheet, is_bom_sheet

from _bompaths import ROOT, OUT  # portable paths; see _bompaths.py
sweep = json.load(open(os.path.join(OUT, "sweep.json"), encoding="utf-8"))
paths = [k["keep"] for k in sweep["kept"]]

records, agg, skipped = [], collections.Counter(), []
t0 = time.time()

for i, p in enumerate(paths, 1):
    rel = os.path.relpath(p, ROOT)
    try:
        wb = read_workbook(p)
    except Exception as ex:
        agg["workbook_read_failed"] += 1
        skipped.append({"file": rel, "error": f"{type(ex).__name__}: {ex}"})
        continue
    if wb.report.get("error"):
        agg["workbook_empty"] += 1
        continue
    agg["workbooks"] += 1
    for sh in wb.sheets:
        agg["sheets_seen"] += 1
        try:
            if not is_bom_sheet(sh):
                agg["sheets_not_bom"] += 1
                continue
            rec = parse_sheet(sh, rel)
            if rec["components"]:
                records.append(rec)
                agg["bom_sheets"] += 1
                agg["components_total"] += len(rec["components"])
                for w in rec["extract_warnings"]:
                    agg["warn_" + w[:34].replace(" ", "_")] += 1
            else:
                agg["bom_like_no_components"] += 1
                skipped.append({"file": rel, "sheet": sh.name,
                                "reason": "bom-like but no component rows"})
        except Exception as ex:
            agg["sheet_parse_failed"] += 1
            skipped.append({"file": rel, "sheet": sh.name,
                            "error": f"{type(ex).__name__}: {ex}"})
    if i % 25 == 0:
        print(f"  ... {i}/{len(paths)}  ({agg['bom_sheets']} BOM sheets)", flush=True)

print("=" * 78)
print("BOM SHEET EXTRACTION")
print("=" * 78)
for k in sorted(agg):
    print(f"  {k:38s} {agg[k]:,}")
print(f"\n  elapsed {time.time()-t0:.0f}s")

# coverage of the fields that matter
cov = collections.Counter()
for r in records:
    h = r["header"]
    for k in ("customer", "swl", "sf", "bag_type", "bag_wt", "loop",
              "top", "bottom", "liner", "doc", "printing", "packing", "colour"):
        if h.get(k) and h[k].get("first") is not None:
            cov[k] += 1
    if any(d["marker"] == "EXTERNAL" for d in r["dims"]):
        cov["dims_external"] += 1
    if any(d["marker"] == "INTERNAL" for d in r["dims"]):
        cov["dims_internal"] += 1
    if r["dims"]:
        cov["dims_any"] += 1
    if r["grand_total"]:
        cov["grand_total"] += 1
    if r["instructions"]:
        cov["instructions"] += 1
    if r["tech"]:
        cov["tech_blocks"] += 1

n = len(records) or 1
print(f"\nFIELD COVERAGE across {len(records)} BOM sheets")
for k, v in sorted(cov.items(), key=lambda kv: -kv[1]):
    print(f"  {k:20s} {v:5d}  {100*v/n:5.1f}%")

json.dump(records, open(os.path.join(OUT, "raw_records.json"), "w",
                        encoding="utf-8"), indent=1, default=str)
json.dump(skipped, open(os.path.join(OUT, "extract_skipped.json"), "w",
                        encoding="utf-8"), indent=1, default=str)
print(f"\nwrote raw_records.json ({len(records)} records)")
print(f"wrote extract_skipped.json ({len(skipped)} entries)")
