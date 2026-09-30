# -*- coding: utf-8 -*-
"""Pass 3: anchor-based extraction of every Anjani 'BILL OF MATERIAL' sheet.
Finds fields by LABEL, not by fixed cell, so layout drift does not break it."""
import os, re, json, warnings, datetime
warnings.filterwarnings("ignore")
import openpyxl

ROOT = r"C:\Users\Nikhil1616\Desktop\BOM\All_Things"
OUT  = r"C:\Users\NIKHIL~1\AppData\Local\Temp\claude\C--Users-Nikhil1616-Desktop-BOM\2c1e7519-df0c-427f-bb17-3b433db17f20\scratchpad"

def S(v):
    if v is None: return ""
    if isinstance(v, datetime.time): return f"{v.hour}:{v.minute:02d}"
    if isinstance(v, datetime.datetime): return v.strftime("%Y-%m-%d")
    return str(v).strip()

def norm(v):
    return re.sub(r"\s+", " ", S(v)).strip().upper()

def num(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool): return float(v)
    s = S(v).replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None

LABELS = {
    "customer":  ["CUSTOMER NAME"],
    "order_no":  ["ORDER NO.", "OEDER NO.", "ORDER NO"],
    "ref_no":    ["REF NO.", "REF NO"],
    "swl":       ["SWL"],
    "sf":        ["SF"],
    "qty":       ["QTY"],
    "bag_type":  ["BAG TYPE"],
    "color":     ["FABRIC COLOR"],
    "bag_wt":    ["BAG WT.", "REQ. WT.", "REW. WT.", "BAG WT", "REQ WT", "REQ. WT",
                  "BAG WEIGHT", "REQUIRED WEIGHT"],
    "printing":  ["PRINTING"],
    "loop":      ["LOOP"],
    "top":       ["SKIRT TOP", "TOP/FS", "TOP / FS", "TOP", "SKIRT/TOP", "TOP /FS"],
    "bottom":    ["BOTTOM/DS", "BOTTOM /DS", "BOTTOM", "BOTTOM/ DS"],
    "doc":       ["DOC PKT", "DOC PKT."],
    "liner":     ["LINER"],
    "packing":   ["PACKING"],
    "mixing":    ["MIXING"],
}

def grid(ws, maxr=90, maxc=26):
    g = {}
    for r in ws.iter_rows(min_row=1, max_row=min(ws.max_row, maxr),
                          max_col=min(ws.max_column, maxc)):
        for c in r:
            if c.value is not None:
                g[(c.row, c.column)] = c.value
    return g

def right_of(g, row, col, span=8):
    """First non-empty cell to the right; also return the whole tail."""
    tail = []
    for cc in range(col + 1, col + 1 + span):
        v = g.get((row, cc))
        if v is not None:
            tail.append(S(v))
    return (tail[0] if tail else ""), " ".join(tail)

def parse_sheet(ws, relpath):
    g = grid(ws)
    flat = " | ".join(norm(v) for v in g.values())
    if "BILL OF MATERIAL" not in flat and "COMPONENT" not in flat:
        return None

    rec = {"file": relpath, "sheet": ws.title}

    # --- header fields by label anchor ------------------------------------
    for key, labs in LABELS.items():
        found = None
        for (r, c), v in g.items():
            n = norm(v).rstrip(":")
            if n in labs:
                first, tail = right_of(g, r, c)
                found = {"first": first, "tail": tail, "at": [r, c]}
                break
        rec[key] = found

    # --- BAG SIZE rows (external / internal) ------------------------------
    dims = []
    for (r, c), v in g.items():
        if norm(v).startswith("BAG SIZE"):
            vals, marker = [], ""
            for cc in range(c + 1, c + 9):
                x = g.get((r, cc))
                if x is None: continue
                n2 = num(x)
                s2 = norm(x)
                if n2 is not None and s2 not in ("CM",) and len(vals) < 3:
                    vals.append(n2)
                elif "EXTERNAL" in s2: marker = "EXTERNAL"
                elif "INTERNAL" in s2: marker = "INTERNAL"
            if len(vals) >= 2:
                dims.append({"row": r, "marker": marker, "vals": vals})
    rec["dims"] = dims

    # --- component table --------------------------------------------------
    hdr_row = None
    for (r, c), v in g.items():
        if norm(v) in ("SR NO.", "SR NO", "SR.NO", "SRNO"):
            hdr_row = r; hdr_col = c; break
    comps, grand = [], None
    if hdr_row:
        # map header names -> column
        colmap = {}
        for cc in range(hdr_col, hdr_col + 14):
            n = norm(g.get((hdr_row, cc)))
            if n: colmap[n] = cc
        rec["header_cells"] = list(colmap.keys())

        def col_for(*cands):
            for cand in cands:
                for k, cc in colmap.items():
                    if cand in k: return cc
            return None

        c_name = col_for("COMPONENT")
        c_gsm  = col_for("GSM")
        c_lam  = col_for("LAMI")
        c_col  = col_for("FABRIC COLOR", "COLOR")
        c_wid  = col_for("FABRIC WIDTH", "WIDTH")
        c_cut  = col_for("CUT LENGTH", "CUT SIZE", "CUT")
        c_wt   = col_for("CUT PIECE WEIGHT", "PCS WEIGHT", "WEIGHT")
        c_rem  = col_for("REMARK")

        for r in range(hdr_row + 1, hdr_row + 26):
            nm = S(g.get((r, c_name))) if c_name else ""
            first = norm(g.get((r, hdr_col)))
            if "GRAND TOTAL" in first or "GRAND TOTAL" in norm(nm):
                grand = num(g.get((r, c_wt))) if c_wt else None
                break
            if not nm.strip(): continue
            comps.append({
                "row": r, "name": nm,
                "gsm":  S(g.get((r, c_gsm)))  if c_gsm else "",
                "lam":  S(g.get((r, c_lam)))  if c_lam else "",
                "color":S(g.get((r, c_col)))  if c_col else "",
                "width":S(g.get((r, c_wid)))  if c_wid else "",
                "cut":  S(g.get((r, c_cut)))  if c_cut else "",
                "wt":   num(g.get((r, c_wt))) if c_wt else None,
                "remark":S(g.get((r, c_rem))) if c_rem else "",
            })
    rec["components"] = comps
    rec["grand_total"] = grand

    # --- instruction lines -------------------------------------------------
    instr = []
    for (r, c), v in g.items():
        s = S(v)
        if re.match(r"^\s*INSTRACTION|^\s*INSTRUCTION", s, re.I) or \
           (c == 1 and re.match(r"^\s*\d\.\s", s) and len(s) > 12):
            instr.append((r, s))
    rec["instructions"] = [s for _, s in sorted(instr)]

    # --- tape plant / loom / needle loom blocks -----------------------------
    tech = {}
    for (r, c), v in g.items():
        n = norm(v)
        for key, lab in [("tape", "TAPE PLANT"), ("loom", "LOOM DEPARTMENT"),
                         ("needle", "NIDDLE LOOM"), ("needle2", "NEEDLE LOOM")]:
            if n == lab:
                blk = []
                for rr in range(r, r + 7):
                    for cc in range(c, c + 6):
                        x = g.get((rr, cc))
                        if x is not None: blk.append(S(x))
                tech[key] = blk
    rec["tech_blocks"] = tech
    return rec

# ---------------------------------------------------------------------------
records, skipped = [], []
for dirpath, _, filenames in os.walk(ROOT):
    for fn in filenames:
        if not fn.lower().endswith((".xlsx", ".xlsm")): continue
        p = os.path.join(dirpath, fn)
        rel = os.path.relpath(p, ROOT)
        try:
            wb = openpyxl.load_workbook(p, data_only=True)
        except Exception as ex:
            skipped.append((rel, str(ex))); continue
        for ws in wb.worksheets:
            try:
                r = parse_sheet(ws, rel)
                if r and r["components"]:
                    records.append(r)
            except Exception as ex:
                skipped.append((f"{rel}::{ws.title}", f"{type(ex).__name__}: {ex}"))
        wb.close()

print(f"PARSED SHEETS WITH A COMPONENT TABLE: {len(records)}")
print(f"SKIPPED: {len(skipped)}")
for s in skipped[:10]: print("   ", s)

json.dump(records, open(os.path.join(OUT, "corpus_allthings.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1, default=str)
print("wrote corpus_allthings.json")
