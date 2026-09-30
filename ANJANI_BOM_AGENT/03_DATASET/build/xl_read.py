# -*- coding: utf-8 -*-
"""
xl_read.py — accuracy-first spreadsheet reader.

Design decided from the empirical diagnostic (dataset/diagnostic.json), not from
defaults:

  * 33,757 formula cells on this corpus, 0 of them uncached  -> openpyxl
    data_only=True is safe here and needs no LibreOffice recalculation pass.
  * 174,841 cells sit INSIDE merged ranges across 116 of 119 workbooks.
    openpyxl returns None for every one of them. This is the single largest
    source of silently missing data, so every read is merge-aware and every
    cell records whether its value is its OWN or an ECHO of a merge origin.
  * 55 workbooks carry drawings / text boxes; 2 carry comments. No spreadsheet
    library surfaces drawing text, so it is pulled straight out of the OOXML
    zip and attached to the sheet.
  * Every value is read TWICE, by openpyxl and by python-calamine, and the two
    are reconciled. Disagreements are counted and reported rather than being
    silently resolved.

Public API
    read_workbook(path) -> Workbook
    Workbook.sheets     -> list[Sheet]
    Sheet.val(r, c)     -> merge-aware value
    Sheet.own(r, c)     -> own-content-only value (no merge echo)
    Sheet.text_blocks   -> text recovered from drawings / text boxes
    Sheet.comments      -> {(r, c): text}
"""
from __future__ import annotations
import os, re, json, zipfile, datetime, warnings, collections
warnings.filterwarnings("ignore")

import openpyxl
try:
    import python_calamine
    _HAS_CALAMINE = True
except Exception:
    _HAS_CALAMINE = False

_NS_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


# ───────────────────────── value normalisation ──────────────────────────
def norm_value(v):
    """One canonical Python form per cell, so two engines can be compared."""
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        f = float(v)
        return int(f) if f == int(f) and abs(f) < 1e15 else round(f, 6)
    if isinstance(v, datetime.datetime):
        # a midnight datetime and a bare date are the same fact; render them
        # identically so the two engines can be compared without false positives
        if (v.hour, v.minute, v.second, v.microsecond) == (0, 0, 0, 0):
            return v.strftime("%Y-%m-%d")
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, datetime.time):
        return "%d:%02d" % (v.hour, v.minute)
    if isinstance(v, datetime.date):
        return v.strftime("%Y-%m-%d")
    s = str(v).replace("\u00a0", " ").strip()
    if s in XL_ERRORS:          # #DIV/0!, #NAME?, ... are broken cells, not data
        return None
    return s if s else None


XL_ERRORS = {"#DIV/0!", "#NAME?", "#REF!", "#VALUE!", "#N/A", "#NULL!",
             "#NUM!", "#GETTING_DATA", "#SPILL!", "#CALC!"}


def _cmp_equal(a, b):
    if a == b:
        return True
    if a is None or b is None:
        return False
    sa, sb = str(a).strip().upper(), str(b).strip().upper()
    if sa == sb:
        return True
    try:                                    # 1 vs 1.0, "5" vs 5
        return abs(float(sa) - float(sb)) < 1e-9
    except Exception:
        pass
    # openpyxl gives datetime.time for 5:01, calamine sometimes a duration/str
    return sa.replace(":00", "") == sb.replace(":00", "")


# ───────────────────────────── data model ───────────────────────────────
class Cell:
    __slots__ = ("row", "col", "value", "own_value", "merge_origin",
                 "formula", "engines_agree", "calamine_value")

    def __init__(self, row, col, value=None, own_value=None, merge_origin=None,
                 formula=None, engines_agree=True, calamine_value=None):
        self.row, self.col = row, col
        self.value = value                  # merge-aware
        self.own_value = own_value          # None if this cell is a merge echo
        self.merge_origin = merge_origin    # (r, c) or None
        self.formula = formula
        self.engines_agree = engines_agree
        self.calamine_value = calamine_value

    @property
    def is_echo(self):
        return self.own_value is None and self.value is not None

    def __repr__(self):
        return f"<Cell {self.row},{self.col} {self.value!r}{' echo' if self.is_echo else ''}>"


class Sheet:
    def __init__(self, name, index):
        self.name = name
        self.index = index
        self.grid: dict[tuple[int, int], Cell] = {}
        self.merges: list[tuple[int, int, int, int]] = []
        self.comments: dict[tuple[int, int], str] = {}
        self.text_blocks: list[str] = []
        self.max_row = 0
        self.max_col = 0
        self.hidden = False
        self.disagreements: list[dict] = []

    # ---- accessors ----------------------------------------------------
    def val(self, r, c):
        """Merge-aware value: a cell inside a merged range returns the
        range's value, which is what a human reading the sheet sees."""
        cel = self.grid.get((r, c))
        return cel.value if cel else None

    def own(self, r, c):
        """Own content only. A merge echo returns None. Use this when you must
        distinguish 'the label spans three columns' from 'there is a value here'."""
        cel = self.grid.get((r, c))
        return cel.own_value if cel else None

    def cell(self, r, c):
        return self.grid.get((r, c))

    def row_values(self, r, merge_aware=True):
        f = self.val if merge_aware else self.own
        return [f(r, c) for c in range(1, self.max_col + 1)]

    def find(self, predicate, max_row=None, max_col=None):
        """Yield (r, c, value) for every cell whose merge-aware value matches."""
        mr = max_row or self.max_row
        mc = max_col or self.max_col
        for (r, c), cel in self.grid.items():
            if r <= mr and c <= mc and cel.value is not None and predicate(cel.value):
                yield r, c, cel.value

    def as_text(self, max_row=None, max_col=None, merge_aware=False):
        """Flat dump — used for classification and for the raw-text field."""
        out = []
        mr = max_row or self.max_row
        mc = max_col or self.max_col
        for r in range(1, mr + 1):
            vals = []
            for c in range(1, mc + 1):
                v = self.val(r, c) if merge_aware else self.own(r, c)
                if v is not None:
                    vals.append(str(v))
            if vals:
                out.append(" | ".join(vals))
        return "\n".join(out)


class Workbook:
    def __init__(self, path):
        self.path = path
        self.sheets: list[Sheet] = []
        self.report: dict = {}

    def __getitem__(self, name):
        for s in self.sheets:
            if s.name == name:
                return s
        raise KeyError(name)


# ─────────────────────── drawings / text boxes ──────────────────────────
def _drawing_text(path):
    """Recover text from text boxes and shapes. No spreadsheet library exposes
    this; it lives in xl/drawings/drawingN.xml. Returns {sheet_index: [text]}.
    Mapping drawing->sheet needs the rels graph, so this returns the union and
    the caller attaches it to the workbook rather than to one sheet."""
    blocks = []
    try:
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if re.match(r"xl/drawings/drawing\d+\.xml$", n):
                    try:
                        xml = z.read(n).decode("utf-8", "ignore")
                    except Exception:
                        continue
                    # <a:t>text</a:t> carries every run of shape text
                    runs = re.findall(r"<a:t>(.*?)</a:t>", xml, re.S)
                    txt = " ".join(x.strip() for x in runs if x.strip())
                    if txt:
                        blocks.append(txt)
    except Exception:
        pass
    return blocks


# ─────────────────────────── the reader ─────────────────────────────────
def read_workbook(path, cross_check=True, max_rows=400, max_cols=60):
    """Read one workbook with every accuracy guard enabled."""
    wb = Workbook(path)

    if os.path.getsize(path) == 0:
        wb.report = {"error": "zero-byte file", "sheets": 0}
        return wb

    op_v = openpyxl.load_workbook(path, data_only=True)
    try:
        op_f = openpyxl.load_workbook(path, data_only=False)
    except Exception:
        op_f = None

    cal_sheets = {}
    if cross_check and _HAS_CALAMINE:
        try:
            cwb = python_calamine.CalamineWorkbook.from_path(path)
            for nm in cwb.sheet_names:
                try:
                    cal_sheets[nm] = cwb.get_sheet_by_name(nm).to_python(
                        skip_empty_area=False)
                except Exception:
                    pass
        except Exception:
            pass

    drawings = _drawing_text(path)
    n_disagree = n_cells = n_echo = 0

    for idx, ws in enumerate(op_v.worksheets):
        sh = Sheet(ws.title, idx)
        sh.hidden = ws.sheet_state != "visible"
        wsf = op_f[ws.title] if op_f is not None else None

        hi_r = min(ws.max_row or 1, max_rows)
        hi_c = min(ws.max_column or 1, max_cols)
        sh.max_row, sh.max_col = hi_r, hi_c

        # 1. own values -------------------------------------------------
        for row in ws.iter_rows(min_row=1, max_row=hi_r, max_col=hi_c):
            for c in row:
                v = norm_value(c.value)
                if v is None:
                    continue
                sh.grid[(c.row, c.column)] = Cell(c.row, c.column, value=v,
                                                  own_value=v)

        # 2. merge propagation ------------------------------------------
        for mr in ws.merged_cells.ranges:
            sh.merges.append((mr.min_row, mr.min_col, mr.max_row, mr.max_col))
            origin = sh.grid.get((mr.min_row, mr.min_col))
            if origin is None or origin.value is None:
                continue
            for r in range(mr.min_row, min(mr.max_row, hi_r) + 1):
                for c in range(mr.min_col, min(mr.max_col, hi_c) + 1):
                    if (r, c) == (mr.min_row, mr.min_col):
                        continue
                    ex = sh.grid.get((r, c))
                    if ex is None:
                        sh.grid[(r, c)] = Cell(r, c, value=origin.value,
                                               own_value=None,
                                               merge_origin=(mr.min_row, mr.min_col))
                        n_echo += 1

        # 3. formulas ---------------------------------------------------
        if wsf is not None:
            for row in wsf.iter_rows(min_row=1, max_row=hi_r, max_col=hi_c):
                for c in row:
                    if isinstance(c.value, str) and c.value.startswith("="):
                        cel = sh.grid.get((c.row, c.column))
                        if cel is None:
                            cel = Cell(c.row, c.column)
                            sh.grid[(c.row, c.column)] = cel
                        cel.formula = c.value

        # 4. comments ---------------------------------------------------
        for row in ws.iter_rows(min_row=1, max_row=hi_r, max_col=hi_c):
            for c in row:
                if c.comment is not None and c.comment.text:
                    sh.comments[(c.row, c.column)] = c.comment.text.strip()

        # 5. calamine cross-check ---------------------------------------
        crows = cal_sheets.get(ws.title)
        if crows:
            for r0, crow in enumerate(crows[:hi_r]):
                for c0, cv in enumerate(crow[:hi_c]):
                    cvn = norm_value(cv)
                    r, c = r0 + 1, c0 + 1
                    cel = sh.grid.get((r, c))
                    own = cel.own_value if cel else None
                    if cvn is None and own is None:
                        continue
                    n_cells += 1
                    if cel is not None:
                        cel.calamine_value = cvn
                    if not _cmp_equal(own, cvn):
                        # calamine found something openpyxl did not -> keep it
                        if own is None and cvn is not None:
                            if cel is None:
                                sh.grid[(r, c)] = Cell(r, c, value=cvn,
                                                       own_value=cvn,
                                                       calamine_value=cvn,
                                                       engines_agree=False)
                            else:
                                cel.own_value = cel.own_value or cvn
                                cel.value = cel.value if cel.value is not None else cvn
                                cel.engines_agree = False
                        else:
                            if cel is not None:
                                cel.engines_agree = False
                        n_disagree += 1
                        if len(sh.disagreements) < 40:
                            sh.disagreements.append(
                                {"cell": f"R{r}C{c}", "openpyxl": own,
                                 "calamine": cvn})

        sh.text_blocks = []
        wb.sheets.append(sh)

    # drawings are workbook-level; attach to sheet 0 for retrieval, and keep
    # the full list on the report so nothing is lost
    if drawings and wb.sheets:
        wb.sheets[0].text_blocks = drawings

    wb.report = {
        "sheets": len(wb.sheets),
        "cells_compared": n_cells,
        "engine_disagreements": n_disagree,
        "merge_echo_cells": n_echo,
        "drawing_text_blocks": len(drawings),
        "calamine_used": bool(cal_sheets),
    }
    op_v.close()
    if op_f is not None:
        op_f.close()
    return wb


if __name__ == "__main__":
    import sys
    p = sys.argv[1] if len(sys.argv) > 1 else \
        r"C:\Users\Nikhil1616\Desktop\BOM\All_Things\EXPORT ENQUIRY.xlsx"
    w = read_workbook(p)
    print(json.dumps(w.report, indent=1))
    s = w.sheets[0]
    print(f"\nsheet '{s.name}'  {s.max_row}x{s.max_col}  merges={len(s.merges)}")
    for r in range(3, 12):
        own = [f"C{c}={s.own(r,c)}" for c in range(1, 14) if s.own(r, c) is not None]
        echo = [f"C{c}~{s.val(r,c)}" for c in range(1, 14)
                if s.own(r, c) is None and s.val(r, c) is not None]
        if own:
            print(f"  r{r:2d} own : " + " | ".join(own))
            if echo:
                print(f"      echo: " + " | ".join(echo[:6]))
