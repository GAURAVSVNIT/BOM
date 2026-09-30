# -*- coding: utf-8 -*-
"""Pass 2: dump a handful of representative BOM sheets in full, to learn layouts."""
import json, warnings, os
warnings.filterwarnings("ignore")
import openpyxl

ROOT = r"C:\Users\Nikhil1616\Desktop\BOM\All_Things"
SAMPLES = [
    ("BOM DOMESTIC\\DOMESTIC ENQUIRY.xlsx", None),
    ("EXPORT ENQUIRY.xlsx", None),
    ("105X105X120 CM BAFFLE BAG.xlsx", None),
    ("90X90X100 CM.xlsx", None),
    ("2 LOOP BAG.xlsx", None),
]

def dump(path, sheetname=None, maxrow=70, maxcol=16):
    wb = openpyxl.load_workbook(path, data_only=True)
    names = wb.sheetnames if sheetname is None else [sheetname]
    for nm in names[:2]:
        ws = wb[nm]
        print("\n" + "#" * 110)
        print(f"# {os.path.basename(path)}  ::  SHEET '{nm}'   ({ws.max_row}r x {ws.max_column}c)")
        print("#" * 110)
        for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, maxrow),
                                max_col=min(ws.max_column, maxcol)):
            cells = []
            for c in row:
                if c.value is None: continue
                v = c.value
                if isinstance(v, float): v = round(v, 3)
                cells.append(f"{c.coordinate}={v!r}")
            if cells:
                print("  " + " | ".join(cells))
    wb.close()

for rel, sh in SAMPLES:
    p = os.path.join(ROOT, rel)
    if os.path.exists(p):
        try: dump(p, sh)
        except Exception as e: print(f"!! {rel}: {e}")
    else:
        print(f"!! missing {rel}")
