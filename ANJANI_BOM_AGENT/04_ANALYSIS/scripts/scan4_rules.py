# -*- coding: utf-8 -*-
"""Pass 4: verify candidate geometry rules against 395 real sheets; catalogue vocabulary."""
import json, re, statistics, collections, os

OUT = r"C:\Users\NIKHIL~1\AppData\Local\Temp\claude\C--Users-Nikhil1616-Desktop-BOM\2c1e7519-df0c-427f-bb17-3b433db17f20\scratchpad"
R = json.load(open(os.path.join(OUT, "corpus_allthings.json"), encoding="utf-8"))
print(f"sheets: {len(R)}\n")

def N(s):
    if s is None: return None
    if isinstance(s, (int, float)): return float(s)
    m = re.search(r"-?\d+(?:\.\d+)?", str(s).replace(",", ""))
    return float(m.group()) if m else None

def U(s): return re.sub(r"\s+", " ", str(s or "")).strip().upper()

# ═══ 1. BAG TYPE RAW VOCABULARY ════════════════════════════════════════════
print("═" * 78)
print("1. BAG TYPE — raw strings the engineer actually writes")
print("═" * 78)
bt = collections.Counter()
for r in R:
    v = (r.get("bag_type") or {}).get("first", "")
    if v.strip(): bt[U(v)] += 1
for k, v in bt.most_common(45):
    print(f"  {v:4d}  {k}")
print(f"  ... {len(bt)} distinct raw strings total\n")

# ═══ 2. COMPONENT NAME VOCABULARY ══════════════════════════════════════════
print("═" * 78)
print("2. COMPONENT NAMES — raw row labels")
print("═" * 78)
cn = collections.Counter()
for r in R:
    for c in r["components"]:
        cn[U(c["name"])] += 1
for k, v in cn.most_common(60):
    print(f"  {v:4d}  {k}")
print(f"  ... {len(cn)} distinct component labels\n")

# ═══ 3. LOOP RULE:  cut = 2*FH + LL + SL ═══════════════════════════════════
print("═" * 78)
print("3. LOOP CUT RULE   candidate:  cut = 2*free_height + LL + SL")
print("═" * 78)
hits = miss = nodata = 0
alts = collections.Counter()
examples = []
for r in R:
    lp = r.get("loop") or {}
    tail = lp.get("tail", "")
    m_q  = re.search(r"(\d+)\s*[Xx*]\s*(\d+)", tail)        # '4X25'
    m_ll = re.search(r"LL\s*[:\-]?\s*(\d+(?:\.\d+)?)", tail, re.I)
    m_sl = re.search(r"SL\s*[:\-]?\s*(\d+(?:\.\d+)?)", tail, re.I)
    loop_row = next((c for c in r["components"]
                     if U(c["name"]) in ("LOOP", "LOOPS", "CORNER LOOP", "LOOP ")), None)
    if not (m_q and m_ll and m_sl and loop_row):
        nodata += 1; continue
    qty, fh = int(m_q.group(1)), float(m_q.group(2))
    LL, SL = float(m_ll.group(1)), float(m_sl.group(1))
    cut = N(loop_row["cut"])
    if cut is None: nodata += 1; continue
    pred = 2 * fh + LL + SL
    if abs(pred - cut) < 0.51:
        hits += 1
    else:
        miss += 1
        d = round(cut - (LL + SL), 1)
        alts[d] += 1
        if len(examples) < 12:
            examples.append((r["file"], r["sheet"], qty, fh, LL, SL, cut, pred))
tot = hits + miss
print(f"  testable sheets: {tot}   (no loop data on {nodata})")
if tot:
    print(f"  EXACT MATCH  2*FH+LL+SL : {hits}/{tot} = {100*hits/tot:.1f}%")
print(f"  residual (cut - LL - SL) when it misses, most common:")
for k, v in alts.most_common(12):
    print(f"      {k:8} cm   x{v}")
print("  misses:")
for e in examples[:8]:
    print(f"      {e[0][:34]:34s} {e[1][:16]:16s} q{e[2]} FH{e[3]} LL{e[4]} SL{e[5]} -> actual {e[6]}, pred {e[7]}")
print()

# ═══ 4. LOOP WEIGHT => implied QTY ═════════════════════════════════════════
print("═" * 78)
print("4. IMPLIED QUANTITY (no qty column exists — it is hidden in the weight)")
print("═" * 78)
qty_by_comp = collections.defaultdict(collections.Counter)
for r in R:
    for c in r["components"]:
        nm, w = U(c["name"]), c["wt"]
        gsm, wid, cut = N(c["gsm"]), N(c["width"]), N(c["cut"])
        if not w or not gsm or not cut: continue
        if "LOOP" in nm or "TIE" in nm or "DDP" in nm or "CORD" in nm:
            unit = gsm * cut / 100.0                      # linear g/m
        elif wid:
            unit = gsm * wid * cut / 10000.0              # area
        else:
            continue
        if unit <= 0: continue
        q = w / unit
        qr = round(q)
        if qr >= 1 and abs(q - qr) / max(q, 1e-9) < 0.02:
            qty_by_comp[nm][qr] += 1
for nm in ["BODY PANEL", "SIDE PANEL", "BOTTOM PANNEL", "BOTTOM PANEL", "TOP PANNEL",
           "TOP PANEL", "LOOP", "BAFFLE", "BAFFLE FABRIC", "FS TIE", "DS TIE",
           "TIE/IRIS ROPE", "TIE", "DDP", "FILLING SPOUT", "D/S", "DOC"]:
    if nm in qty_by_comp:
        c = qty_by_comp[nm]
        tot = sum(c.values())
        dist = "  ".join(f"qty{k}:{v}({100*v/tot:.0f}%)" for k, v in sorted(c.items())[:6])
        print(f"  {nm:18s} n={tot:4d}   {dist}")
print()

# ═══ 5. PANEL GEOMETRY BY FAMILY ═══════════════════════════════════════════
print("═" * 78)
print("5. PANEL GEOMETRY — actual widths/cuts vs external dims")
print("═" * 78)
def family(raw):
    s = U(raw)
    if "BAFFLE" in s: return "baffle"
    if "U+2" in s or "U + 2" in s or "U-PANEL" in s or "U PANEL" in s or "UPANEL" in s: return "u_panel"
    if "CIRCULAR" in s or "TUBULAR" in s: return "circular"
    if "4 PANNEL" in s or "4-PANNEL" in s or "4 PANEL" in s or "4-PANEL" in s: return "four_panel"
    if "2 PANNEL" in s or "2 PANEL" in s or "C-TYPE" in s or "TYPE - C" in s: return "two_panel"
    if "SINGLE LOOP" in s or "1 LOOP" in s: return "single_loop"
    if "2 LOOP" in s or "TWO LOOP" in s or "DOUBLE LOOP" in s: return "two_loop"
    if "OMEGA" in s: return "omega"
    if "TUNNEL" in s: return "tunnel"
    return "other"

resid = collections.defaultdict(lambda: collections.defaultdict(list))
famct = collections.Counter()
for r in R:
    fam = family((r.get("bag_type") or {}).get("first", ""))
    famct[fam] += 1
    ext = next((d["vals"] for d in r["dims"] if d["marker"] == "EXTERNAL"), None)
    if not ext or len(ext) < 3: continue
    L, W, H = ext[0], ext[1], ext[2]
    for c in r["components"]:
        nm = U(c["name"]); wid, cut = N(c["width"]), N(c["cut"])
        if not wid or not cut: continue
        if "BODY" in nm:
            resid[fam]["BODY.width - W"].append(round(wid - W, 1))
            resid[fam]["BODY.cut - (2H+L)"].append(round(cut - (2 * H + L), 1))
            resid[fam]["BODY.cut - H"].append(round(cut - H, 1))
            resid[fam]["BODY.width - 2(W+L)"].append(round(wid - 2 * (W + L), 1))
        elif "SIDE" in nm:
            resid[fam]["SIDE.width - L"].append(round(wid - L, 1))
            resid[fam]["SIDE.cut - H"].append(round(cut - H, 1))
        elif "TOP PAN" in nm:
            resid[fam]["TOPPANEL.width - L"].append(round(wid - L, 1))
            resid[fam]["TOPPANEL.cut - W"].append(round(cut - W, 1))
        elif "BOTTOM PAN" in nm:
            resid[fam]["BOTPANEL.width - L"].append(round(wid - L, 1))
            resid[fam]["BOTPANEL.cut - W"].append(round(cut - W, 1))

print("family counts:", dict(famct.most_common()))
for fam in ["u_panel", "circular", "baffle", "four_panel", "two_panel"]:
    if fam not in resid: continue
    print(f"\n  --- {fam} ---")
    for k, vals in resid[fam].items():
        vals = [v for v in vals if v is not None]
        if len(vals) < 8: continue
        c = collections.Counter(vals)
        top = c.most_common(4)
        share = 100 * top[0][1] / len(vals)
        print(f"    {k:26s} n={len(vals):4d}  mode={top[0][0]:>7} ({share:4.0f}%)  "
              f"next={[t[0] for t in top[1:4]]}  median={statistics.median(vals):.1f}")
print()

# ═══ 6. LAMINATION NOTATION ════════════════════════════════════════════════
print("═" * 78)
print("6. LAMINATION / REMARK NOTATION  (e.g. '170+30 LAMINATED')")
print("═" * 78)
lam = collections.Counter()
for r in R:
    for c in r["components"]:
        s = U(c["remark"])
        if re.search(r"\d+\s*\+\s*\d+", s): lam[s] += 1
for k, v in lam.most_common(25): print(f"  {v:4d}  {k}")
print()

# ═══ 7. INSTRUCTION LINE VOCABULARY ════════════════════════════════════════
print("═" * 78)
print("7. PRODUCTION INSTRUCTION LINES — the free text under the table")
print("═" * 78)
ins = collections.Counter()
for r in R:
    for s in r["instructions"]:
        s2 = re.sub(r"^\s*(INSTRACTION|INSTRUCTION)\s*:?-?\s*", "", str(s), flags=re.I)
        s2 = re.sub(r"^\s*\d\.\s*", "", s2)
        s2 = U(s2)
        if 8 < len(s2) < 120: ins[s2] += 1
for k, v in ins.most_common(45): print(f"  {v:4d}  {k}")
print(f"  ... {len(ins)} distinct instruction lines\n")

# ═══ 8. MIXING RECIPES ═════════════════════════════════════════════════════
print("═" * 78)
print("8. RM MIXING RECIPES")
print("═" * 78)
mx = collections.Counter()
for r in R:
    m = r.get("mixing") or {}
    t = U(m.get("tail", ""))
    if "PP" in t: mx[t] += 1
for k, v in mx.most_common(20): print(f"  {v:4d}  {k}")
print()

# ═══ 9. TARGET vs GRAND TOTAL ══════════════════════════════════════════════
print("═" * 78)
print("9. STATED BAG WEIGHT vs GRAND TOTAL OF COMPONENTS")
print("═" * 78)
gaps = []
for r in R:
    bw = (r.get("bag_wt") or {}).get("first", "")
    t = N(bw); g = r.get("grand_total")
    if t is None or not g: continue
    if t < 50: t *= 1000                       # kg -> g
    if g < 50: g *= 1000
    if t <= 0 or g <= 0: continue
    gaps.append(abs(g - t) / t * 100)
gaps.sort()
if gaps:
    print(f"  n={len(gaps)}   median {statistics.median(gaps):.2f}%   "
          f"within1% {100*sum(1 for x in gaps if x<=1)/len(gaps):.0f}%   "
          f"within2% {100*sum(1 for x in gaps if x<=2)/len(gaps):.0f}%   "
          f"within5% {100*sum(1 for x in gaps if x<=5)/len(gaps):.0f}%   "
          f"within10% {100*sum(1 for x in gaps if x<=10)/len(gaps):.0f}%")
print()

# ═══ 10. WHICH ROWS ARE ALWAYS PRESENT ═════════════════════════════════════
print("═" * 78)
print("10. ROW PRESENCE — non-zero weight, i.e. actually fitted")
print("═" * 78)
present = collections.Counter(); listed = collections.Counter()
for r in R:
    for c in r["components"]:
        nm = U(c["name"]); listed[nm] += 1
        if c["wt"]: present[nm] += 1
for nm, n in listed.most_common(28):
    p = present[nm]
    print(f"  {nm:22s} listed {n:4d}   fitted {p:4d}   ({100*p/n:5.1f}% of sheets that list it)")
