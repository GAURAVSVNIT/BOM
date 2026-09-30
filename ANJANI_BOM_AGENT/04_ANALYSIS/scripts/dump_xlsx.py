import sys, openpyxl
from openpyxl.utils import get_column_letter

path = sys.argv[1]
wb = openpyxl.load_workbook(path, data_only=True)
print("WORKBOOK:", path)
print("SHEETS:", wb.sheetnames)
for ws in wb.worksheets:
    print("\n" + "=" * 100)
    print(f"SHEET: {ws.title}   dims={ws.dimensions}  max_row={ws.max_row} max_col={ws.max_column}")
    print("=" * 100)
    if ws.merged_cells.ranges:
        print("MERGED:", [str(r) for r in ws.merged_cells.ranges][:40])
    for row in ws.iter_rows(min_row=1, max_row=min(ws.max_row, 200), max_col=min(ws.max_column, 30)):
        cells = []
        for c in row:
            v = c.value
            if v is None:
                continue
            if isinstance(v, float):
                v = round(v, 4)
            cells.append(f"{c.coordinate}={v!r}")
        if cells:
            print(" | ".join(cells))
