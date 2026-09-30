# -*- coding: utf-8 -*-
"""
02_reconcile.py — run the multi-engine reader over every unique workbook and
report, corpus-wide, exactly how much the two engines disagree and how much
data merge-awareness recovers. This is the accuracy evidence for the dataset.
"""
import os, sys, json, collections, warnings, re, zipfile
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xl_read import read_workbook

from _bompaths import ROOT, OUT  # portable paths; see _bompaths.py
sweep = json.load(open(os.path.join(OUT, "sweep.json"), encoding="utf-8"))
paths = [k["keep"] for k in sweep["kept"]]

agg = collections.Counter()
per_file = []
real_disagreements = []
drawing_text_found = []

for i, p in enumerate(paths, 1):
    rel = os.path.relpath(p, ROOT)
    try:
        wb = read_workbook(p)
    except Exception as ex:
        agg["read_failed"] += 1
        per_file.append({"file": rel, "error": f"{type(ex).__name__}: {ex}"})
        continue

    if wb.report.get("error"):
        agg["empty_file"] += 1
        per_file.append({"file": rel, **wb.report})
        continue

    agg["workbooks_ok"] += 1
    agg["sheets"] += wb.report["sheets"]
    agg["cells_compared"] += wb.report["cells_compared"]
    agg["engine_disagreements"] += wb.report["engine_disagreements"]
    agg["merge_echo_cells"] += wb.report["merge_echo_cells"]
    if wb.report["calamine_used"]:
        agg["calamine_used"] += 1

    for s in wb.sheets:
        for d in s.disagreements:
            real_disagreements.append({"file": rel, "sheet": s.name, **d})
        if s.text_blocks:
            drawing_text_found.append({"file": rel,
                                       "n": len(s.text_blocks),
                                       "sample": s.text_blocks[0][:160]})

    per_file.append({"file": rel, **wb.report})
    if i % 25 == 0:
        print(f"  ... {i}/{len(paths)}", flush=True)

print("=" * 78)
print("CORPUS-WIDE EXTRACTION RECONCILIATION")
print("=" * 78)
for k in sorted(agg):
    print(f"  {k:26s} {agg[k]:,}")

cc = agg["cells_compared"] or 1
print(f"\n  engine agreement rate      {100*(1-agg['engine_disagreements']/cc):.4f}%")
print(f"  cells recovered by merge   {agg['merge_echo_cells']:,}"
      f"  ({100*agg['merge_echo_cells']/cc:.1f}% of compared cells)")

print(f"\n--- REAL disagreements after date normalisation: {len(real_disagreements)} ---")
kinds = collections.Counter()
for d in real_disagreements:
    o, c = d["openpyxl"], d["calamine"]
    if o is None:
        kinds["openpyxl MISSED a value calamine found"] += 1
    elif c is None:
        kinds["calamine missed a value openpyxl found"] += 1
    else:
        kinds["both present, values differ"] += 1
for k, v in kinds.most_common():
    print(f"   {v:5d}  {k}")
for d in real_disagreements[:15]:
    print(f"     {d['file'][:42]:42s} {d['sheet'][:16]:16s} {d['cell']:8s} "
          f"op={str(d['openpyxl'])[:22]!r} cal={str(d['calamine'])[:22]!r}")

print(f"\n--- drawings / text boxes carrying TEXT: {len(drawing_text_found)} workbooks ---")
for d in drawing_text_found[:15]:
    print(f"   {d['n']:3d} blocks  {d['file'][:44]:44s} {d['sample'][:70]!r}")

json.dump({"aggregate": dict(agg), "per_file": per_file,
           "disagreements": real_disagreements[:500],
           "drawing_text": drawing_text_found},
          open(os.path.join(OUT, "reconciliation.json"), "w", encoding="utf-8"),
          indent=1, default=str)
print(f"\nwrote {os.path.join(OUT,'reconciliation.json')}")
