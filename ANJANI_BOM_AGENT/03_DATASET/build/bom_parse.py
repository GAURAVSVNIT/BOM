# -*- coding: utf-8 -*-
"""
bom_parse.py — parse one Anjani "BILL OF MATERIAL" sheet into a raw record.

Built on xl_read's merge-aware grid. The critical improvement over a naive
label-anchored scan: when we look to the right of a label for its value, we
must skip cells that are merge ECHOES OF THE LABEL ITSELF. On these sheets a
label routinely spans 2-3 columns, so a naive "first non-empty cell to the
right" returns the label again.

Extracts:
    header      A3:C11 + G3:L11 by label anchor
    dims        external / internal size rows
    components  the 15-row table, with merged COMPONENT spans handled
    instructions the INSTRACTION free-text block
    tech        TAPE PLANT / LOOM DEPARTMENT / NIDDLE LOOM blocks
    mixing      the RM blend line
    raw_text    a flat dump, used for classification and for adapter A
"""
from __future__ import annotations
import re, math, collections

# ── header labels ───────────────────────────────────────────────────────
LABELS = {
    "customer":  ["CUSTOMER NAME", "CUSTOMER"],
    "order_no":  ["ORDER NO.", "OEDER NO.", "ORDER NO", "ORDER NUMBER"],
    "ref_no":    ["REF NO.", "REF NO", "REFERENCE NO"],
    "swl":       ["SWL", "S.W.L", "S W L"],
    "sf":        ["SF", "S.F", "SAFETY FACTOR"],
    "qty":       ["QTY", "QUANTITY"],
    "bag_type":  ["BAG TYPE", "BAG TYPE "],
    "colour":    ["FABRIC COLOR", "FABRIC COLOUR"],
    "bag_wt":    ["BAG WT.", "BAG WT", "REQ. WT.", "REQ WT.", "REQ. WT",
                  "REQ WT", "REW. WT.", "REW WT.", "BAG WEIGHT",
                  "REQUIRED WEIGHT", "REQ. WEIGHT"],
    "printing":  ["PRINTING"],
    "loop":      ["LOOP"],
    # NB "TOP SPOUT" is the single most common variant (219 sheets) and was
    # missing from the first cut of this list.
    "top":       ["SKIRT TOP", "TOP/FS", "TOP / FS", "TOP /FS", "SKIRT/TOP",
                  "TOP/SKIRT", "TOP SPOUT", "TOP/SKT", "TOP / SKT",
                  "INLET / TOP", "INLET/TOP", "INLET SPOUT", "TOP SKIRT",
                  "SKIRT / DUFFLE FABRIC", "SKIRT/DUFFLE", "TOP FLAP",
                  "OPEN TOP", "TOP"],
    "bottom":    ["BOTTOM/DS", "BOTTOM /DS", "BOTTOM/ DS", "BOTTOM / DS",
                  "BOTTOM SPOUT", "OUTLET SPOUT", "OUTLET / BOTTOM",
                  "BOTTOM"],
    "doc":       ["DOC PKT", "DOC PKT.", "DOC POCKET", "DOCUMENT POCKET"],
    "liner":     ["LINER"],
    "packing":   ["PACKING", "CONTAINER DATE"],
    "mixing":    ["MIXING"],
}

COMPONENT_HEADERS = {
    "sr":     ["SR NO.", "SR NO", "SR.NO", "SRNO", "S.NO", "SR"],
    "name":   ["COMPONENT"],
    "gsm":    ["GSM"],
    "lami":   ["LAMI/UL", "LAMI", "LAMINATION"],
    "colour": ["FABRIC COLOR", "FABRIC COLOUR", "COLOR", "COLOUR"],
    # a second sheet layout exists (21 sheets): SR.NO. | COMPONENT |
    # FABRIC SIZE CM | CUT SIZE | QTY | GSM  — it carries an EXPLICIT qty column
    "width":  ["FABRIC WIDTH (CM)", "FABRIC WIDTH", "FABRIC SIZE CM",
               "FABRIC SIZE", "WIDTH (CM)", "WIDTH"],
    "cut":    ["CUT LENGTH(CM)", "CUT LENGTH (CM)", "CUT LENGTH", "CUT SIZE (CM)",
               "CUT SIZE", "CUT"],
    "weight": ["CUT PIECE WEIGHT", "PCS WEIGHT", "CUT PIECE WEIGHT ", "WEIGHT"],
    "qty":    ["QTY", "PCS", "PIECE PER BAG", "PCS PER BAG", "NO OF PCS",
               "QUANTITY"],
    "total":  ["TOTAL", "TARGET"],
    "remark": ["REMARK", "REMARKS"],
}

TOTAL_MARKERS = ("GRAND TOTAL", "TOTAL BAG WEIGHT", "TOTAL WEIGHT", "TOTAL")

TECH_BLOCKS = ["TAPE PLANT", "LOOM DEPARTMENT", "NIDDLE LOOM", "NEEDLE LOOM"]


def U(x):
    return re.sub(r"\s+", " ", str(x if x is not None else "")).strip().upper()


def num(x):
    if x is None:
        return None
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    m = re.search(r"-?\d+(?:\.\d+)?", str(x).replace(",", ""))
    return float(m.group()) if m else None


# ── merge-aware right scan ──────────────────────────────────────────────
def scan_right(sheet, row, col, span=10):
    """Values to the right of a label, skipping echoes of the label's own
    merged range. Returns (first_value, joined_tail, [(col, value), ...])."""
    origin_cell = sheet.cell(row, col)
    label_origin = (row, col)
    if origin_cell is not None and origin_cell.merge_origin:
        label_origin = origin_cell.merge_origin

    seen_origins = {label_origin}
    out = []
    for c in range(col + 1, col + 1 + span):
        cel = sheet.cell(row, c)
        if cel is None or cel.value is None:
            continue
        this_origin = cel.merge_origin or (row, c)
        if this_origin in seen_origins:      # echo of something already taken
            continue
        seen_origins.add(this_origin)
        out.append((c, cel.value))
    first = out[0][1] if out else None
    tail = " ".join(str(v) for _, v in out)
    return first, tail, out


def find_label(sheet, names, max_row=60, max_col=30):
    """Locate a label cell by its OWN content (never by a merge echo)."""
    want = {U(n) for n in names}
    best = None
    for (r, c), cel in sheet.grid.items():
        if r > max_row or c > max_col or cel.own_value is None:
            continue
        n = U(cel.own_value).rstrip(":").rstrip("-").strip()
        if n in want:
            if best is None or (r, c) < best[:2]:
                best = (r, c, cel.own_value)
    return best


# ── sheet classification ────────────────────────────────────────────────
def is_bom_sheet(sheet):
    txt = sheet.as_text(max_row=45, max_col=25, merge_aware=False).upper()
    if "BILL OF MATERIAL" in txt:
        return True
    hits = sum(1 for k in ("COMPONENT", "GSM", "CUT LENGTH", "GRAND TOTAL",
                           "BAG SIZE", "BODY PANEL", "SWL")
               if k in txt)
    return hits >= 4


# ── main parser ─────────────────────────────────────────────────────────
def parse_sheet(sheet, source_file):
    rec = {
        "source_file": source_file,
        "sheet": sheet.name,
        "sheet_index": sheet.index,
        "n_merges": len(sheet.merges),
        "extract_warnings": [],
    }

    # ---------- header fields -------------------------------------------
    header = {}
    for key, names in LABELS.items():
        # header block always sits in the first ~20 rows; searching further
        # down lets component names such as "TOP PANEL" masquerade as labels
        hit = find_label(sheet, names, max_row=20)
        if not hit:
            header[key] = None
            continue
        r, c, lbl = hit
        first, tail, cells = scan_right(sheet, r, c)
        header[key] = {"label": lbl, "at": [r, c], "first": first,
                       "tail": tail, "cells": [[cc, vv] for cc, vv in cells]}
    rec["header"] = header

    # ---------- BAG SIZE rows (external / internal) ----------------------
    dims = []
    for (r, c), cel in list(sheet.grid.items()):
        if cel.own_value is None:
            continue
        if not U(cel.own_value).startswith("BAG SIZE"):
            continue
        _, _, cells = scan_right(sheet, r, c, span=12)
        vals, marker, unit = [], None, None
        for cc, vv in cells:
            n = num(vv)
            s = U(vv)
            if s in ("CM", "MM", "INCH", "IN"):
                unit = s
            elif "EXTERNAL" in s or s == "OD":
                marker = "EXTERNAL"
            elif "INTERNAL" in s or s == "ID":
                marker = "INTERNAL"
            elif n is not None and len(vals) < 3:
                vals.append(n)
        if len(vals) >= 2:
            dims.append({"row": r, "marker": marker, "unit": unit or "CM",
                         "vals": vals})
    rec["dims"] = dims

    # ---------- component table ------------------------------------------
    hdr = None
    for names in (COMPONENT_HEADERS["sr"], COMPONENT_HEADERS["name"]):
        hdr = find_label(sheet, names, max_row=40)
        if hdr:
            break
    comps, grand = [], None
    colmap = {}
    if hdr:
        hr, hc, _ = hdr
        # map every header cell on that row, using OWN values so a merged
        # header span does not register twice
        row_hdrs = []
        for c in range(1, sheet.max_col + 1):
            v = sheet.own(hr, c)
            if v is not None:
                row_hdrs.append((c, U(v)))
        for key, cands in COMPONENT_HEADERS.items():
            for c, txt in row_hdrs:
                if any(txt == U(x) for x in cands):
                    colmap[key] = c
                    break
            if key not in colmap:            # fall back to substring
                for c, txt in row_hdrs:
                    if any(U(x) in txt for x in cands):
                        colmap.setdefault(key, c)
                        break
        rec["component_header_row"] = hr
        rec["component_colmap"] = colmap

        c_name = colmap.get("name")
        if c_name:
            for r in range(hr + 1, hr + 30):
                first_txt = U(sheet.val(r, colmap.get("sr", 1)))
                name_v = sheet.val(r, c_name)
                # the COMPONENT header is often merged over two columns; if the
                # mapped column is empty look one to the right before giving up
                if name_v is None:
                    name_v = sheet.val(r, c_name + 1)
                name = U(name_v)
                row_txt = " ".join(str(sheet.val(r, cc)) for cc in
                                   range(1, min(sheet.max_col, 6) + 1)
                                   if sheet.val(r, cc) is not None).upper()
                if any(m in first_txt or m in name or m in row_txt
                       for m in TOTAL_MARKERS):
                    gcol = colmap.get("weight")
                    grand = num(sheet.val(r, gcol)) if gcol else None
                    if grand is None:
                        for cc in range(1, sheet.max_col + 1):
                            g = num(sheet.val(r, cc))
                            if g and g > 50:
                                grand = g
                                break
                    break
                if not name:
                    continue
                get = lambda k: sheet.val(r, colmap[k]) if k in colmap else None
                comps.append({
                    "row": r,
                    "name": str(name_v).strip(),
                    "gsm": get("gsm"),
                    "lami": get("lami"),
                    "colour": get("colour"),
                    "width": get("width"),
                    "cut": get("cut"),
                    "weight": num(get("weight")),
                    "qty_stated": num(get("qty")),   # present in the 2nd layout
                    "total": get("total"),
                    "remark": get("remark"),
                })
    rec["components"] = comps
    rec["grand_total"] = grand
    if hdr and not comps:
        rec["extract_warnings"].append("component header found but no rows parsed")

    # ---------- instructions ---------------------------------------------
    instr = []
    for (r, c), cel in sheet.grid.items():
        if cel.own_value is None or c > 4:
            continue
        s = str(cel.own_value).strip()
        if re.match(r"^\s*(INSTRACTION|INSTRUCTION)", s, re.I):
            instr.append((r, s))
        elif re.match(r"^\s*\d\s*[\.\)]\s+\S", s) and len(s) > 12:
            instr.append((r, s))
    rec["instructions"] = [s for _, s in sorted(instr)]

    # ---------- tape / loom / needle-loom ---------------------------------
    tech = {}
    for lab in TECH_BLOCKS:
        hit = find_label(sheet, [lab], max_row=80, max_col=30)
        if not hit:
            continue
        r, c, _ = hit
        blk = []
        for rr in range(r, min(r + 8, sheet.max_row + 1)):
            row = []
            for cc in range(c, min(c + 7, sheet.max_col + 1)):
                v = sheet.val(rr, cc)
                if v is not None:
                    row.append(str(v))
            if row:
                blk.append(row)
        tech[lab.lower().replace(" ", "_")] = blk
    rec["tech"] = tech

    # ---------- drawings / comments --------------------------------------
    if sheet.text_blocks:
        rec["drawing_text"] = sheet.text_blocks
    if sheet.comments:
        rec["comments"] = {f"R{r}C{c}": t for (r, c), t in sheet.comments.items()}

    # ---------- raw text --------------------------------------------------
    rec["raw_text"] = sheet.as_text(max_row=60, max_col=26, merge_aware=False)

    # ---------- quality flags ---------------------------------------------
    if not rec["dims"]:
        rec["extract_warnings"].append("no BAG SIZE row found")
    if grand is None and comps:
        rec["extract_warnings"].append("no GRAND TOTAL found")
    return rec
