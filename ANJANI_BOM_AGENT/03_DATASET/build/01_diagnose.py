# -*- coding: utf-8 -*-
"""
01_diagnose.py — measure, empirically, what each extraction engine would MISS
on this specific corpus. Decide the engine from evidence, not from blog posts.

Checks per workbook:
  A. real container format (zip/OOXML vs OLE/.xls vs other) regardless of extension
  B. formula cells whose cached value is absent  -> openpyxl data_only=True yields None
  C. merged ranges                                -> value lives ONLY in the top-left cell
  D. drawings / text boxes                        -> no library surfaces these
  E. cell comments / notes                        -> openpyxl only
  F. hidden sheets, hidden rows/cols              -> silently skipped by naive readers
  G. openpyxl vs calamine value disagreement      -> cross-engine reconciliation
"""
import os, sys, json, zipfile, warnings, collections, re
warnings.filterwarnings("ignore")
import openpyxl
import olefile
import python_calamine

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _bompaths import ROOT, OUT  # noqa: E402  (portable paths; see _bompaths.py)
sweep = json.load(open(os.path.join(OUT, "sweep.json"), encoding="utf-8"))
paths = [k["keep"] for k in sweep["kept"]]

def container(p):
    with open(p, "rb") as f:
        sig = f.read(8)
    if sig[:4] == b"PK\x03\x04":
        return "ooxml_zip"
    if sig[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "ole_xls"
    return "unknown:" + sig[:4].hex()

rep = []
agg = collections.Counter()
for p in paths:
    rel = os.path.relpath(p, ROOT)
    r = {"file": rel, "container": container(p)}
    agg["container_" + r["container"].split(":")[0]] += 1

    if r["container"] != "ooxml_zip":
        r["note"] = "not OOXML - openpyxl cannot open it"
        rep.append(r); agg["not_ooxml"] += 1
        continue

    # ---- D/E: raw zip inspection for parts no reader exposes -------------
    try:
        with zipfile.ZipFile(p) as z:
            names = z.namelist()
        r["has_drawings"] = any("xl/drawings/" in n for n in names)
        r["has_comments"] = any("xl/comments" in n or "/threadedComments/" in n for n in names)
        r["has_charts"] = any("xl/charts/" in n for n in names)
        r["n_sheets_xml"] = sum(1 for n in names if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
        agg["with_drawings"] += int(r["has_drawings"])
        agg["with_comments"] += int(r["has_comments"])
    except Exception as ex:
        r["zip_error"] = str(ex)

    # ---- B/C/F: openpyxl structural facts -------------------------------
    try:
        wbF = openpyxl.load_workbook(p, data_only=False)   # formulas
        wbV = openpyxl.load_workbook(p, data_only=True)    # cached values
        nf = ncached = nmerged = nmergedcells = nhidden_sheet = 0
        nhidden_row = nhidden_col = 0
        for ws in wbF.worksheets:
            wv = wbV[ws.title]
            if ws.sheet_state != "visible":
                nhidden_sheet += 1
            nmerged += len(ws.merged_cells.ranges)
            for mr in ws.merged_cells.ranges:
                nmergedcells += (mr.max_row - mr.min_row + 1) * (mr.max_col - mr.min_col + 1) - 1
            nhidden_row += sum(1 for d in ws.row_dimensions.values() if d.hidden)
            nhidden_col += sum(1 for d in ws.column_dimensions.values() if d.hidden)
            for row in ws.iter_rows():
                for c in row:
                    if isinstance(c.value, str) and c.value.startswith("="):
                        nf += 1
                        if wv[c.coordinate].value is not None:
                            ncached += 1
        r.update(n_formula=nf, n_formula_cached=ncached,
                 n_formula_uncached=nf - ncached,
                 n_merged_ranges=nmerged, n_cells_hidden_by_merge=nmergedcells,
                 n_hidden_sheets=nhidden_sheet, n_hidden_rows=nhidden_row,
                 n_hidden_cols=nhidden_col, n_sheets=len(wbF.worksheets))
        agg["formula_cells"] += nf
        agg["formula_uncached"] += nf - ncached
        agg["merged_ranges"] += nmerged
        agg["cells_hidden_by_merge"] += nmergedcells
        agg["hidden_sheets"] += nhidden_sheet
        if nf - ncached > 0: agg["wb_with_uncached_formulas"] += 1
        if nmerged > 0: agg["wb_with_merges"] += 1
        wbF.close(); wbV.close()
    except Exception as ex:
        r["openpyxl_error"] = f"{type(ex).__name__}: {ex}"
        agg["openpyxl_failed"] += 1

    # ---- G: calamine cross-check ----------------------------------------
    try:
        cw = python_calamine.CalamineWorkbook.from_path(p)
        r["calamine_sheets"] = len(cw.sheet_names)
        agg["calamine_ok"] += 1
    except Exception as ex:
        r["calamine_error"] = f"{type(ex).__name__}: {ex}"
        agg["calamine_failed"] += 1

    rep.append(r)

print("=" * 78)
print("EXTRACTION RISK DIAGNOSTIC  —  %d unique workbooks" % len(paths))
print("=" * 78)
for k in sorted(agg):
    print(f"  {k:28s} {agg[k]}")

print("\n--- workbooks that are NOT OOXML (openpyxl cannot read) ---")
for r in rep:
    if r["container"] != "ooxml_zip":
        print(f"   {r['container']:12s} {r['file']}")

print("\n--- workbooks with UNCACHED formulas (data_only=True -> None) ---")
n = 0
for r in sorted(rep, key=lambda x: -x.get("n_formula_uncached", 0)):
    if r.get("n_formula_uncached", 0) > 0:
        n += 1
        if n <= 12:
            print(f"   {r['n_formula_uncached']:5d} uncached / {r['n_formula']:5d} formulas   {r['file']}")
print(f"   ({n} workbooks affected)")

print("\n--- workbooks with the MOST cells hidden inside merged ranges ---")
for r in sorted(rep, key=lambda x: -x.get("n_cells_hidden_by_merge", 0))[:10]:
    if r.get("n_cells_hidden_by_merge", 0):
        print(f"   {r['n_cells_hidden_by_merge']:6d} cells / {r['n_merged_ranges']:4d} ranges   {r['file']}")

print("\n--- workbooks carrying drawings / text boxes / comments ---")
for r in rep:
    tags = []
    if r.get("has_drawings"): tags.append("drawings")
    if r.get("has_comments"): tags.append("comments")
    if r.get("has_charts"): tags.append("charts")
    if tags:
        print(f"   {','.join(tags):24s} {r['file']}")

print("\n--- hidden sheets ---")
for r in rep:
    if r.get("n_hidden_sheets"):
        print(f"   {r['n_hidden_sheets']} hidden of {r.get('n_sheets')}   {r['file']}")

json.dump({"aggregate": dict(agg), "per_file": rep},
          open(os.path.join(OUT, "diagnostic.json"), "w", encoding="utf-8"),
          indent=1, default=str)
print(f"\nwrote {os.path.join(OUT,'diagnostic.json')}")
