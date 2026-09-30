# -*- coding: utf-8 -*-
"""
04_gold.py — build the four gold layers.

    OrderSpec_gold     what the customer asked for   (HEADER BLOCK ONLY)
    BuildSpec_gold     what the engineer decided     (header + components + notes)
    PhysicalBOM_gold   what was actually cut         (component table verbatim)
    Clarification_gold what the agent should ask     (derived from absent fields)

THE FIREWALL: build_order_spec() receives only the header dict and the dims.
It is never handed `components`. If a BuildSpec field leaked into OrderSpec the
extractor would learn to predict engineering decisions from the enquiry, and the
whole evaluation would be meaningless while looking excellent.
"""
import os, sys, re, json, math, hashlib, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rules as R

from _bompaths import ROOT, OUT, GOLD  # portable paths; see _bompaths.py
os.makedirs(GOLD, exist_ok=True)

recs = json.load(open(os.path.join(OUT, "raw_records.json"), encoding="utf-8"))


def U(x):
    return re.sub(r"\s+", " ", str(x if x is not None else "")).strip().upper()


def num(x):
    if x is None:
        return None
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    m = re.search(r"-?\d+(?:\.\d+)?", str(x).replace(",", ""))
    return float(m.group()) if m else None


def F(value, state="provided", evidence=None, source=None):
    d = {"value": value, "state": state}
    if evidence:
        d["evidence"] = str(evidence)[:180]
    if source:
        d["source"] = source
    return d


NOT_SPEC = {"", "NA", "N/A", "-", "--", "NIL", "NONE", "NO", "0", "X"}


def hv(header, key):
    """header value + the raw cell text it came from"""
    h = header.get(key)
    if not h:
        return None, None
    v = h.get("first")
    return v, h.get("tail")


# ═════════════ weight / unit helpers ════════════════════════════════════
def to_grams(x):
    """'1.427 KG' -> 1427 ; '880' -> 880 ; '0.88 Kg' -> 880"""
    if x is None:
        return None
    s = U(x)
    n = num(s)
    if n is None:
        return None
    if "KG" in s or (n < 50 and n > 0):     # a bag is never under 50 g
        return n * 1000.0
    return n


def parse_sf(x):
    s = U(x)
    m = re.match(r"(\d+)\s*[:\.]\s*0?(\d+)", s)
    if m:
        return f"{int(m.group(1))}:{int(m.group(2))}"
    m = re.match(r"(\d+)$", s)
    if m and int(m.group(1)) in (5, 6):
        return f"{m.group(1)}:1"
    return None


def parse_spout(text):
    """'40x50 CM WITH IRISH CLOSER' -> (40, 50, 'iris')"""
    if not text:
        return None, None, None
    s = U(text)
    m = re.search(r"(\d+(?:\.\d+)?)\s*[Xx*]\s*(\d+(?:\.\d+)?)", s)
    d, h = (float(m.group(1)), float(m.group(2))) if m else (None, None)
    cl = None
    if "IRIS" in s or "IRISH" in s:
        cl = "iris"
    elif "PETAL" in s or "PETEL" in s:
        cl = "petal"
    elif "PYJAMA" in s or "PYAJAMA" in s or "PYSAMA" in s:
        cl = "pyjama"
    elif "TIE" in s:
        cl = "tied"
    elif "OPEN" in s or "NORMAL" in s or "SIMPLE" in s or "PLAIN" in s:
        cl = "open"
    return d, h, cl


def parse_loop(tail):
    """'4X25 LL 60 CM SL 40 CM white 50 MM/WHITE' -> qty, fh, LL, SL, mm, colour"""
    s = U(tail or "")
    qty = fh = LL = SL = mm = None
    m = re.search(r"(\d+)\s*[Xx*]\s*(\d+(?:\.\d+)?)", s)
    if m:
        qty, fh = int(m.group(1)), float(m.group(2))
    m = re.search(r"\bLL\s*[:\-]?\s*(\d+(?:\.\d+)?)", s)
    if m:
        LL = float(m.group(1))
    m = re.search(r"\bSL\s*[:\-]?\s*(\d+(?:\.\d+)?)", s)
    if m:
        SL = float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*MM", s)
    if m:
        mm = float(m.group(1))
    col = None
    for c in ("WHITE", "BLUE", "BLACK", "GREEN", "YELLOW", "RED", "ORANGE", "GREY"):
        if c in s:
            col = c
            break
    return qty, fh, LL, SL, mm, col


def yes_no(x):
    if x is None:
        return None
    s = U(x)
    if s in NOT_SPEC:
        return None
    if s.startswith("Y") or "YES" in s:
        return True
    if s.startswith("N") and "NO" in s:
        return False
    return True          # any concrete spec means it is fitted


# ═════════════ 1. ORDER SPEC — header block only ════════════════════════
def build_order_spec(header, dims, source_file, sheet, raw_text):
    """FIREWALL: components are deliberately NOT a parameter of this function."""
    o = {"_id": None, "source": {"file": source_file, "sheet": sheet,
                                 "type": "bom_sheet_header"}}

    cust, _ = hv(header, "customer")
    o["customer"] = F(str(cust).strip(), "provided", cust) if cust else F(None, "not_specified")

    order, _ = hv(header, "order_no")
    o["order_no"] = F(str(order).strip(), "provided", order) if order else F(None, "not_specified")

    # dimensions
    ext = next((d["vals"] for d in dims if d["marker"] == "EXTERNAL"), None)
    itn = next((d["vals"] for d in dims if d["marker"] == "INTERNAL"), None)
    if ext is None and itn is None and dims:
        ext = dims[0]["vals"]
    for tag, vals in (("ext", ext), ("int", itn)):
        for i, ax in enumerate(("L", "W", "H")):
            k = f"{tag}_{ax}_cm"
            o[k] = F(vals[i], "provided") if (vals and len(vals) > i) else F(None, "not_specified")

    swl, swl_raw = hv(header, "swl")
    n = num(swl)
    o["swl_kg"] = F(n, "provided", swl_raw) if n else F(None, "not_specified")

    sf, sf_raw = hv(header, "sf")
    p = parse_sf(sf)
    o["sf"] = F(p, "provided", sf_raw) if p else F(None, "not_specified")

    qty, _ = hv(header, "qty")
    o["order_qty"] = F(num(qty), "provided", qty) if num(qty) else F(None, "not_specified")

    bw, bw_raw = hv(header, "bag_wt")
    g = to_grams(bw)
    lbl = U(header.get("bag_wt", {}).get("label") if header.get("bag_wt") else "")
    # "BAG WT." = what Anjani quoted back; "REQ. WT." = what the customer asked
    key = "req_weight_g" if lbl.startswith("REQ") or lbl.startswith("REW") else "quoted_weight_g"
    o["req_weight_g"] = F(None, "not_specified")
    o["quoted_weight_g"] = F(None, "not_specified")
    if g:
        o[key] = F(round(g, 2), "provided", bw_raw)

    bt, bt_raw = hv(header, "bag_type")
    o["stated_bag_type_raw"] = F(str(bt).strip(), "provided", bt_raw) if bt else F(None, "not_specified")

    col, _ = hv(header, "colour")
    o["fabric_colour"] = F(U(col), "provided", col) if col and U(col) not in NOT_SPEC else F(None, "not_specified")

    # loop line
    lp = header.get("loop") or {}
    q, fh, LL, SL, mm, lcol = parse_loop(lp.get("tail"))
    o["loop_qty"] = F(q, "provided", lp.get("tail")) if q else F(None, "not_specified")
    o["loop_free_height_cm"] = F(fh, "provided") if fh else F(None, "not_specified")
    o["loop_LL_cm"] = F(LL, "provided") if LL else F(None, "not_specified")
    o["loop_SL_cm"] = F(SL, "provided") if SL else F(None, "not_specified")
    o["belt_width_mm"] = F(mm, "provided") if mm else F(None, "not_specified")
    o["loop_colour"] = F(lcol, "provided") if lcol else F(None, "not_specified")

    # top / bottom
    tp = header.get("top") or {}
    tlabel, ttail = U(tp.get("label")), tp.get("tail")
    td, th, tcl = parse_spout(ttail)
    if "OPEN TOP" in tlabel or (ttail and "OPEN" in U(ttail) and not td):
        o["top_type"] = F("OPEN_TOP", "provided", ttail)
    elif "SKIRT" in tlabel or "DUFFLE" in tlabel or (ttail and "SKIRT" in U(ttail)):
        o["top_type"] = F("SKIRT", "provided", ttail)
    elif "FLAP" in tlabel:
        o["top_type"] = F("TOP_FLAP", "provided", ttail)
    elif td:
        o["top_type"] = F("FS_SPOUT", "provided", ttail)
    else:
        o["top_type"] = F(None, "not_specified")
    o["fs_dia_cm"] = F(td, "provided") if td else F(None, "not_specified")
    o["fs_height_cm"] = F(th, "provided") if th else F(None, "not_specified")
    o["fs_closure"] = F(tcl, "provided") if tcl else F(None, "not_specified")

    bt2 = header.get("bottom") or {}
    btail = bt2.get("tail")
    bd, bh, bcl = parse_spout(btail)
    if btail and ("CLOSED" in U(btail) or "FLAT" in U(btail) or "PLAIN" in U(btail)) and not bd:
        o["bottom_type"] = F("FLAT_BOTTOM", "provided", btail)
    elif bd:
        o["bottom_type"] = F("DS_SPOUT", "provided", btail)
    elif btail and U(btail) in NOT_SPEC:
        o["bottom_type"] = F("FLAT_BOTTOM", "provided", btail)
    else:
        o["bottom_type"] = F(None, "not_specified")
    o["ds_dia_cm"] = F(bd, "provided") if bd else F(None, "not_specified")
    o["ds_height_cm"] = F(bh, "provided") if bh else F(None, "not_specified")
    o["ds_closure"] = F(bcl, "provided") if bcl else F(None, "not_specified")

    # accessory intentions — never inferred, only read
    for key, hk in (("has_liner", "liner"), ("has_doc_pocket", "doc"),
                    ("has_printing", "printing")):
        v, tail = hv(header, hk)
        s = U(v)
        if v is None or s in NOT_SPEC:
            o[key] = F(False, "provided", tail) if s in ("NA", "NO", "N/A") \
                else F(None, "not_specified")
        else:
            o[key] = F(True, "provided", tail)
    lv, ltail = hv(header, "liner")
    m = re.search(r"(\d+)\s*MIC", U(ltail or ""))
    o["liner_micron"] = F(float(m.group(1)), "provided", ltail) if m else F(None, "not_specified")

    pk, pktail = hv(header, "packing")
    o["packing"] = F(str(pk).strip(), "provided", pktail) if pk and U(pk) not in NOT_SPEC \
        else F(None, "not_specified")

    pr, prtail = hv(header, "printing")
    m = re.search(r"(\d+)\s*SIDE", U(prtail or ""))
    o["printing_sides"] = F(int(m.group(1)), "provided", prtail) if m else F(None, "not_specified")

    # product / contents — the field C1 says explains the GSM spread. It is
    # almost never on these sheets; captured so the schema is ready for it.
    o["product_contents"] = F(None, "not_specified")
    o["static_type"] = F("C", "provided", "conductive") if "CONDUCT" in U(raw_text) \
        else F(None, "not_specified")

    o["raw_text"] = raw_text
    return o


# ═════════════ 2. PHYSICAL BOM — the component table verbatim ═══════════
def build_physical(rec):
    comps, flags = [], []
    for c in rec["components"]:
        canon = R.canon_component(c["name"])
        gsm, w, cut = num(c["gsm"]), num(c["width"]), num(c["cut"])
        wt = c.get("weight")
        qty_stated = c.get("qty_stated")
        # recover implicit quantity by reconciling the recorded weight
        qty_implied, basis = None, None
        if wt and cut:
            if canon in ("CORNER LOOP", "STEVEDORE LOOP", "EXTRA LOOP", "TIE",
                         "FS TIE", "DS TIE", "IRIS TIE", "DDP", "FILLER CORD",
                         "ROPE", "FULL BODY LOOP"):
                unit = R.tape_weight(gsm, cut, 1) if gsm else None
                basis = "linear"
            elif gsm and w:
                unit = R.fabric_weight(gsm, w, cut, 1, 1)
                basis = "area"
            else:
                unit = None
            if unit and unit > 0:
                q = wt / unit
                if abs(q - round(q)) / max(q, 1e-9) < 0.02 and 1 <= round(q) <= 16:
                    qty_implied = int(round(q))
        comps.append({
            "raw_name": c["name"], "canonical": canon,
            "gsm": gsm, "width_cm": w, "cut_cm": cut, "weight_g": wt,
            "qty_stated": qty_stated, "qty_implied": qty_implied,
            "qty_basis": basis,
            "lami": c.get("lami"), "colour": c.get("colour"),
            "remark": c.get("remark"),
        })
        if canon is None and U(c["name"]) not in ("", "0"):
            flags.append(f"uncanonical:{U(c['name'])[:26]}")
    total = sum(x["weight_g"] or 0 for x in comps)
    grand = rec.get("grand_total")
    if grand and total and abs(total - grand) / grand > 0.02:
        flags.append(f"component_sum_vs_grand_total_{100*abs(total-grand)/grand:.1f}pct")
    return {"components": comps, "component_sum_g": round(total, 3),
            "grand_total_g": grand, "integrity_flags": flags}


# ═════════════ 3. BUILD SPEC — what the engineer decided ════════════════
def build_build_spec(rec, order, phys):
    h = rec["header"]
    raw_type = (order["stated_bag_type_raw"]["value"] or "") + " " + \
               U(h.get("loop", {}).get("tail") if h.get("loop") else "")
    belt_mm = order["belt_width_mm"]["value"]
    fam, fam_src = R.classify_family(raw_type, belt_mm)
    loop_t, loop_src = R.classify_loop_type(raw_type, belt_mm)

    by = {}
    for c in phys["components"]:
        if c["canonical"]:
            by.setdefault(c["canonical"], c)

    def fitted(name):
        c = by.get(name)
        return bool(c and (c["weight_g"] or 0) > 0)

    body = by.get("BODY PANEL") or {}
    loop = by.get("CORNER LOOP") or {}
    baf = by.get("BAFFLE") or {}
    bot = by.get("BOTTOM PANEL") or {}
    top = by.get("TOP PANEL") or {}
    fs = by.get("FILLING SPOUT") or {}
    ds = by.get("DISCHARGE SPOUT") or {}
    st = by.get("STITCHING") or {}

    instr = " || ".join(rec.get("instructions", []))
    iu = U(instr)

    dust = "NONE"
    if fitted("FELT"):
        dust = "TRIPLE"
    elif fitted("DDP") or "DOUBLE DUST" in iu:
        dust = "DOUBLE"
    elif fitted("FILLER CORD") or "DUST PROOF" in iu:
        dust = "SINGLE"

    b = {
        "family": fam,
        "loop_type": loop_t,
        "static_type": order["static_type"]["value"] or "A",
        "double_layer": bool(re.search(r"DOUBLE\s*LAYER", U(raw_type))),
        "top_type": order["top_type"]["value"] or ("TOP_PANEL" if fitted("TOP PANEL")
                                                   else "OPEN_TOP"),
        "bottom_type": order["bottom_type"]["value"] or ("DS_SPOUT" if fitted("DISCHARGE SPOUT")
                                                         else "FLAT_BOTTOM"),

        "body_gsm": body.get("gsm"),
        "bottom_gsm": bot.get("gsm"),
        "top_gsm": top.get("gsm"),
        "spout_gsm": fs.get("gsm") or ds.get("gsm"),
        "baffle_gsm": baf.get("gsm"),
        "fabric_colour": order["fabric_colour"]["value"],
        "body_laminated": bool(re.search(r"LAMIN", U(body.get("lami")))) or
                          bool(re.search(r"\d+\s*\+\s*\d+", U(body.get("remark")))),

        "loop_qty": order["loop_qty"]["value"] or loop.get("qty_implied") or 4,
        "belt_width_mm": belt_mm,
        "belt_gpm": loop.get("gsm"),
        "loop_free_height_cm": order["loop_free_height_cm"]["value"],
        "loop_attach_long_cm": order["loop_LL_cm"]["value"],
        "loop_attach_short_cm": order["loop_SL_cm"]["value"],
        "loop_colour": order["loop_colour"]["value"],

        "has_baffle": fitted("BAFFLE"),
        "has_liner": fitted("LINER"),
        "liner_micron": order["liner_micron"]["value"],
        "has_doc_pocket": fitted("DOC POCKET"),
        "dust_proof": dust,
        "has_felt": fitted("FELT"),
        "has_glue": fitted("GLUE"),
        "has_tabbing_tape": fitted("TABBING TAPE"),
        "has_b_lock": fitted("B-LOCK"),
        "has_rope": fitted("ROPE"),
        "has_stevedore": fitted("STEVEDORE LOOP"),
        "has_belly_band": fitted("BELLY BAND"),
        "has_top_band": fitted("TOP BAND"),
        "has_loop_protector": fitted("LOOP PROTECTOR"),
        "has_extra_loop": fitted("EXTRA LOOP"),
        "has_label": fitted("LABEL"),
        "printing_sides": order["printing_sides"]["value"] or
                          (1 if fitted("PRINTING") else 0),

        "fs_dia_cm": order["fs_dia_cm"]["value"],
        "fs_height_cm": order["fs_height_cm"]["value"],
        "fs_closure": order["fs_closure"]["value"],
        "ds_dia_cm": order["ds_dia_cm"]["value"],
        "ds_height_cm": order["ds_height_cm"]["value"],
        "ds_closure": order["ds_closure"]["value"],

        "yarn_weight_g": st.get("weight_g"),
        "stitch_spec": ("DOUBLE_CHAIN" if "DOUBLE CHAIN" in iu else
                        "DOUBLE_NEEDLE" if "DOUBLE NEEDLE" in iu else
                        "OVERLOCK_CHAIN"),
        "fold_spec": "J_FOLD" if ("J FOLD" in iu or "J-FOLD" in iu) else "OUT_FOLD",
        "packing": order["packing"]["value"],
        "instruction_lines": rec.get("instructions", [])[:8],
        "_provenance": {"family": fam_src, "loop_type": loop_src},
    }
    return b


# ═════════════ 4. CLARIFICATION — what to ask ═══════════════════════════
QUESTION = {
    "swl_kg": ("SWL_MISSING", "Safe working load is not stated. Please confirm the SWL, "
               "or give the product and fill volume so we can compute it."),
    "sf": ("SF_MISSING", "Safety factor is not stated. Single-trip (5:1) or multi-trip (6:1)?"),
    "ext_L_cm": ("SIZE_MISSING", "Bag size is not stated. Please confirm L x W x H in cm."),
    "req_weight_g": ("TARGET_WEIGHT_MISSING",
                     "No required bag weight given. We will build to the load chart and "
                     "report the resulting weight — please confirm that is acceptable."),
    "stated_bag_type_raw": ("CONSTRUCTION_NOT_STATED",
                            "Construction not stated. We have assumed U+2 panel with corner "
                            "loop, our house default. Please confirm."),
    "loop_LL_cm": ("LOOP_LENGTH_ASSUMED",
                   "Loop attachment lengths not stated. We have assumed LL = 65% and "
                   "SL = 35% of bag height with 25 cm free height. Please confirm."),
    "product_contents": ("PRODUCT_NOT_STATED",
                         "What product will the bag carry? It determines the fabric GSM."),
    "has_liner": ("LINER_NOT_STATED", "No liner specified — we will not fit one. Confirm."),
    "static_type": ("STATIC_TYPE_NOT_STATED",
                    "Static protection type not stated. Type A assumed (non-flammable "
                    "contents only). Confirm if the product is a flammable powder."),
}
BLOCKING = {"swl_kg", "ext_L_cm"}


def build_clarification(order, build):
    blocking, advisory, assumptions = [], [], []
    for field, (code, q) in QUESTION.items():
        f = order.get(field)
        if f and f["state"] == "not_specified":
            item = {"code": code, "field": field, "question": q}
            (blocking if field in BLOCKING else advisory).append(item)
    if order["stated_bag_type_raw"]["state"] == "not_specified":
        assumptions.append({"field": "family", "value": build["family"],
                            "reason": "not stated; house default U+2"})
    if order["top_type"]["state"] == "not_specified":
        assumptions.append({"field": "top_type", "value": build["top_type"],
                            "reason": "not stated; OPEN_TOP default"})
    if order["has_liner"]["state"] == "not_specified":
        assumptions.append({"field": "has_liner", "value": False,
                            "reason": "never added silently"})
    # feasibility: stated GSM below the chart floor
    swl, sf = order["swl_kg"]["value"], order["sf"]["value"]
    if swl and sf and build.get("body_gsm"):
        floor = R.gsm_floor(swl, int(sf.split(":")[0]), build["loop_type"])
        if floor and build["body_gsm"] < floor:
            advisory.append({
                "code": "GSM_BELOW_CHART", "field": "body_gsm",
                "question": (f"Body GSM {build['body_gsm']:.0f} is below our "
                             f"{floor} GSM standard for SWL {swl:.0f} kg at {sf}. "
                             f"Confirm you want us to proceed."),
                "chart_floor": floor, "chosen": build["body_gsm"]})
    return {"blocking": blocking, "advisory": advisory,
            "assumptions_made": assumptions,
            "n_questions": len(blocking) + len(advisory)}


# ═════════════ drive ════════════════════════════════════════════════════
order_rows, build_rows, phys_rows, clar_rows = [], [], [], []
agg = collections.Counter()

for rec in recs:
    try:
        o = build_order_spec(rec["header"], rec["dims"], rec["source_file"],
                             rec["sheet"], rec.get("raw_text", ""))
        p = build_physical(rec)
        b = build_build_spec(rec, o, p)
        c = build_clarification(o, b)
    except Exception as ex:
        agg["gold_failed"] += 1
        continue

    key = "|".join(str(o[k]["value"]) for k in
                   ("ext_L_cm", "ext_W_cm", "ext_H_cm", "swl_kg", "sf",
                    "top_type", "bottom_type", "req_weight_g"))
    fp = hashlib.sha1((b["family"] + "|" + key).encode()).hexdigest()[:16]
    rid = hashlib.sha1((rec["source_file"] + "::" + rec["sheet"]).encode()).hexdigest()[:12]

    o["_id"] = rid
    for d in (o, b, p, c):
        d["_id"] = rid
        d["_fingerprint"] = fp
        d["_source"] = {"file": rec["source_file"], "sheet": rec["sheet"]}

    order_rows.append(o); build_rows.append(b)
    phys_rows.append(p); clar_rows.append(c)
    agg["ok"] += 1
    agg["family_" + b["family"]] += 1
    if p["integrity_flags"]:
        agg["with_integrity_flags"] += 1

# ── FIREWALL TEST ───────────────────────────────────────────────────────
BUILD_ONLY = {"body_gsm", "belt_gpm", "yarn_weight_g", "baffle_gsm",
              "bottom_gsm", "top_gsm", "spout_gsm", "dust_proof", "fold_spec",
              "stitch_spec", "has_baffle", "has_felt"}
leak = [k for k in order_rows[0].keys() if k in BUILD_ONLY] if order_rows else []
assert not leak, f"FIREWALL BREACH: BuildSpec fields present in OrderSpec: {leak}"

for name, rows in (("order_spec", order_rows), ("build_spec", build_rows),
                   ("physical_bom", phys_rows), ("clarification", clar_rows)):
    with open(os.path.join(GOLD, name + ".jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")

print("=" * 78)
print("GOLD LAYERS")
print("=" * 78)
print(f"  FIREWALL TEST: PASS — no BuildSpec field appears in OrderSpec")
for k in sorted(agg):
    print(f"  {k:34s} {agg[k]}")

# coverage
cov = collections.Counter()
for o in order_rows:
    for k, v in o.items():
        if isinstance(v, dict) and v.get("state") == "provided":
            cov[k] += 1
n = len(order_rows) or 1
print(f"\nORDERSPEC FIELD COVERAGE ({n} records)")
for k, v in sorted(cov.items(), key=lambda kv: -kv[1]):
    print(f"  {k:24s} {v:5d}  {100*v/n:5.1f}%")

bc = collections.Counter()
for b in build_rows:
    for k, v in b.items():
        if not k.startswith("_") and v not in (None, "", [], False):
            bc[k] += 1
print(f"\nBUILDSPEC FIELD COVERAGE")
for k, v in sorted(bc.items(), key=lambda kv: -kv[1])[:26]:
    print(f"  {k:24s} {v:5d}  {100*v/n:5.1f}%")

q = collections.Counter()
for c in clar_rows:
    for item in c["blocking"] + c["advisory"]:
        q[item["code"]] += 1
print(f"\nCLARIFICATION CODES RAISED")
for k, v in q.most_common():
    print(f"  {k:28s} {v:5d}")

print(f"\nfingerprint groups: {len({o['_fingerprint'] for o in order_rows})}")
print(f"wrote 4 files to {GOLD}")
