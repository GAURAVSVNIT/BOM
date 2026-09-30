# -*- coding: utf-8 -*-
"""Test the engineer's stated rules against the 395-sheet corpus."""
import json, re, os, collections, statistics
OUT = r"C:\Users\NIKHIL~1\AppData\Local\Temp\claude\C--Users-Nikhil1616-Desktop-BOM\2c1e7519-df0c-427f-bb17-3b433db17f20\scratchpad"
R = json.load(open(os.path.join(OUT, "corpus_allthings.json"), encoding="utf-8"))
def N(s):
    if s is None: return None
    if isinstance(s,(int,float)): return float(s)
    m = re.search(r"-?\d+(?:\.\d+)?", str(s).replace(",",""))
    return float(m.group()) if m else None
def U(s): return re.sub(r"\s+"," ",str(s or "")).strip().upper()
def fam(raw):
    s=U(raw)
    if "BAFFLE" in s: return "baffle"
    if "U+2" in s or "U-PAN" in s or "U PAN" in s or "UPANEL" in s: return "u_panel"
    if "CIRCULAR" in s or "TUBELAR" in s or "TUBULAR" in s: return "circular"
    if re.search(r"\b4[\s-]*PAN", s): return "four_panel"
    if "SINGLE LOOP" in s: return "single_loop"
    if "2 LOOP" in s or "DOUBLE LOOP" in s: return "two_loop"
    return "other"

# ══ B1: "+8 standard; +10 when body GSM < 120 AND height > 100" ═══════════
print("="*78); print("B1  U-panel body cut: engineer says +8 standard, +10 when GSM<120 AND H>100")
print("="*78)
cells = collections.defaultdict(collections.Counter)
rows=[]
for r in R:
    if fam((r.get("bag_type") or {}).get("first","")) != "u_panel": continue
    ext = next((d["vals"] for d in r["dims"] if d["marker"]=="EXTERNAL"), None)
    if not ext or len(ext)<3: continue
    L,W,H = ext
    b = next((c for c in r["components"] if "BODY" in U(c["name"])), None)
    if not b: continue
    cut, gsm = N(b["cut"]), N(b["gsm"])
    if cut is None or gsm is None: continue
    resid = round(cut-(2*H+L),1)
    key = ("GSM<120" if gsm<120 else "GSM>=120", "H>100" if H>100 else "H<=100")
    cells[key][resid]+=1
    rows.append((gsm,H,resid))
for k in [("GSM<120","H>100"),("GSM<120","H<=100"),("GSM>=120","H>100"),("GSM>=120","H<=100")]:
    c = cells.get(k, collections.Counter())
    tot = sum(c.values())
    if not tot: print(f"  {k[0]:9s} {k[1]:8s}  n=0"); continue
    top = c.most_common(4)
    p10 = 100*c.get(10.0,0)/tot; p8 = 100*c.get(8.0,0)/tot
    print(f"  {k[0]:9s} {k[1]:8s}  n={tot:4d}   +10:{p10:5.1f}%   +8:{p8:5.1f}%   top={top}")
print("\n  ENGINEER'S RULE PREDICTS: +10 only in the (GSM<120, H>100) cell, +8 elsewhere.")

# ══ B7: spout formulas ════════════════════════════════════════════════════
print("\n"+"="*78); print("B7  Spout: cut = D*3.14 + 12 ;  FS width = H+5 ;  DS width = H+8")
print("="*78)
def spout_test(kind, labels, wid_add):
    hits=miss=0; ex=[]
    for r in R:
        hdr = (r.get("top") if kind=="FS" else r.get("bottom")) or {}
        t = U(hdr.get("tail",""))
        m = re.search(r"(\d+(?:\.\d+)?)\s*[Xx*]\s*(\d+(?:\.\d+)?)\s*CM", t)
        if not m: continue
        D, Hh = float(m.group(1)), float(m.group(2))
        comp = next((c for c in r["components"] if U(c["name"]) in labels), None)
        if not comp: continue
        w, cut = N(comp["width"]), N(comp["cut"])
        if not w or not cut: continue
        pred_cut = round(D*3.14+12, 1)
        if abs(pred_cut-cut) <= 1.5: hits+=1
        else:
            miss+=1
            if len(ex)<5: ex.append((r["sheet"][:22], D, Hh, cut, pred_cut, w, Hh+wid_add))
    tot=hits+miss
    print(f"  {kind} cut = D*3.14+12 : {hits}/{tot} = {100*hits/max(tot,1):.1f}% within 1.5 cm")
    for e in ex: print(f"      {e[0]:22s} D{e[1]} H{e[2]}  cut {e[3]} (pred {e[4]})  width {e[5]} (pred {e[6]})")
spout_test("FS", {"FILLING SPOUT","FS SPOUT","F/S","TOP SPOUT","TOP / FS"}, 5)
spout_test("DS", {"D/S","D SPOUT","DS SPOUT","DISCHARGE SPOUT","BOTTOM SPOUT"}, 8)

# ══ B8: iris tie = D*3.14 + 38 ════════════════════════════════════════════
print("\n"+"="*78); print("B8  Iris tie cut = D*3.14 + 38")
print("="*78)
hits=miss=0; ex=[]
for r in R:
    bot = U((r.get("bottom") or {}).get("tail",""))
    if "IRIS" not in bot and "IRISH" not in bot: continue
    m = re.search(r"(\d+(?:\.\d+)?)\s*[Xx*]\s*(\d+(?:\.\d+)?)\s*CM", bot)
    if not m: continue
    D = float(m.group(1))
    comp = next((c for c in r["components"] if U(c["name"]) in
                 {"TIE/IRIS ROPE","IRISH TIE","TIE/IRIS"}), None)
    if not comp: continue
    cut = N(comp["cut"])
    if not cut: continue
    pred = round(D*3.14+38,1)
    if abs(pred-cut)<=2: hits+=1
    else:
        miss+=1
        if len(ex)<6: ex.append((r["sheet"][:22], D, cut, pred))
tot=hits+miss
print(f"  {hits}/{tot} = {100*hits/max(tot,1):.1f}% within 2 cm")
for e in ex: print(f"      {e[0]:22s} D{e[1]}  actual {e[2]}  pred {e[3]}")

# ══ F1: yarn weight per family ════════════════════════════════════════════
print("\n"+"="*78); print("F1  Yarn: U+2=45g  circular=60g  single_loop=35g  baffle=72g")
print("="*78)
yb = collections.defaultdict(list)
for r in R:
    f = fam((r.get("bag_type") or {}).get("first",""))
    s = next((c for c in r["components"] if U(c["name"])=="STITCHING"), None)
    if s and s["wt"]: yb[f].append(s["wt"])
claim = {"u_panel":45,"circular":60,"single_loop":35,"baffle":72}
for f,v in sorted(yb.items(), key=lambda kv:-len(kv[1])):
    if len(v)<5: continue
    md = statistics.median(v)
    c = collections.Counter(round(x) for x in v).most_common(4)
    tag = f"  claim {claim[f]}g" if f in claim else ""
    print(f"  {f:12s} n={len(v):4d}  median {md:5.1f}g  mode {c}{tag}")

# ══ D5: belt strength 1 g = 35 kg ═════════════════════════════════════════
print("\n"+"="*78); print("D5  Belt: 1 g/m carries 35 kg  ->  gpm*35*qty >= SWL*SF ?")
print("="*78)
ok=bad=0; ex=[]
for r in R:
    swl = N((r.get("swl") or {}).get("first",""))
    sfs = U((r.get("sf") or {}).get("first",""))
    m = re.match(r"(\d+):", sfs)
    if not (swl and m): continue
    sf = float(m.group(1))
    lp = next((c for c in r["components"] if U(c["name"]) in ("LOOP","LOOPS")), None)
    if not lp: continue
    gpm = N(lp["gsm"])
    if not gpm: continue
    cap = gpm*35*4
    need = swl*sf
    if cap >= need: ok+=1
    else:
        bad+=1
        if len(ex)<6: ex.append((r["sheet"][:22], swl, sf, gpm, round(cap), round(need)))
tot=ok+bad
print(f"  satisfied on {ok}/{tot} = {100*ok/max(tot,1):.1f}% of sheets")
print("  shortfalls:")
for e in ex: print(f"      {e[0]:22s} SWL{e[1]:6.0f} SF{e[2]:.0f} gpm{e[3]:5.1f}  cap {e[4]:6d} < need {e[5]}")
