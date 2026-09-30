# -*- coding: utf-8 -*-
"""Pass 1: inventory every workbook/sheet under All_Things and classify it."""
import os, sys, json, warnings, traceback
warnings.filterwarnings("ignore")
import openpyxl

ROOT = r"C:\Users\Nikhil1616\Desktop\BOM\All_Things"
OUT  = r"C:\Users\NIKHIL~1\AppData\Local\Temp\claude\C--Users-Nikhil1616-Desktop-BOM\2c1e7519-df0c-427f-bb17-3b433db17f20\scratchpad"

BOM_MARKERS = ["COMPONENT", "GSM", "CUT SIZE", "CUT LENGTH", "GRAND TOTAL",
               "BAG SIZE", "WIDTH", "BODY", "LOOP", "SWL"]

def cellstr(v):
    if v is None: return ""
    return str(v).strip().upper()

inv = []
errors = []
files = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    for fn in filenames:
        files.append(os.path.join(dirpath, fn))

ext_count = {}
for f in files:
    e = os.path.splitext(f)[1].lower()
    ext_count[e] = ext_count.get(e, 0) + 1

print("FILES UNDER All_Things:", len(files))
print("BY EXTENSION:", json.dumps(ext_count, indent=2))
print()

xlsx = [f for f in files if f.lower().endswith((".xlsx", ".xlsm"))]
print("XLSX/XLSM workbooks:", len(xlsx))

for path in xlsx:
    rel = os.path.relpath(path, ROOT)
    try:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    except Exception as ex:
        errors.append({"file": rel, "error": f"{type(ex).__name__}: {ex}"})
        continue
    for ws in wb.worksheets:
        try:
            vals = []
            nrow = 0
            for row in ws.iter_rows(min_row=1, max_row=80, max_col=25, values_only=True):
                nrow += 1
                for v in row:
                    s = cellstr(v)
                    if s:
                        vals.append(s)
            blob = " | ".join(vals)
            score = sum(1 for m in BOM_MARKERS if m in blob)
            inv.append({
                "file": rel, "sheet": ws.title,
                "max_row": ws.max_row, "max_col": ws.max_column,
                "marker_score": score,
                "is_bom_like": score >= 4,
                "head": vals[:60],
            })
        except Exception as ex:
            errors.append({"file": rel, "sheet": ws.title,
                           "error": f"{type(ex).__name__}: {ex}"})
    try: wb.close()
    except Exception: pass

bomlike = [r for r in inv if r["is_bom_like"]]
print(f"\nSHEETS TOTAL: {len(inv)}")
print(f"BOM-LIKE SHEETS: {len(bomlike)}")
print(f"WORKBOOKS WITH >1 BOM-LIKE SHEET: "
      f"{len({r['file'] for r in bomlike}) } workbooks hold them")

from collections import Counter
per_wb = Counter(r["file"] for r in bomlike)
print("\nTOP WORKBOOKS BY BOM-SHEET COUNT:")
for f, n in per_wb.most_common(25):
    print(f"  {n:3d}  {f}")

print(f"\nERRORS: {len(errors)}")
for e in errors[:25]:
    print("  ", e)

json.dump({"inventory": inv, "errors": errors},
          open(os.path.join(OUT, "inv1.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nwrote inv1.json")
