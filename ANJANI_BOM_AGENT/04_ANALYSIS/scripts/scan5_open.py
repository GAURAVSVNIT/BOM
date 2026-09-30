# -*- coding: utf-8 -*-
"""Pass 5: isolate the genuinely ambiguous decisions -> these become the questions."""
import json, re, statistics, collections, os
OUT = r"C:\Users\NIKHIL~1\AppData\Local\Temp\claude\C--Users-Nikhil1616-Desktop-BOM\2c1e7519-df0c-427f-bb17-3b433db17f20\scratchpad"
R = json.load(open(os.path.join(OUT, "corpus_allthings.json"), encoding="utf-8"))

def N(s):
    if s is None: return None
    if isinstance(s, (int, float)): return float(s)
    m = re.search(r"-?\d+(?:\.\d+)?", str(s).replace(",", ""))
    return float(m.group()) if m else None
def U(s): return re.sub(r"\s+", " ", str(s or "")).strip().upper()
def fam(raw):
    s = U(raw)
    if "BAFFLE" in s: return "baffle"
    if "U+2" in s or "U-PAN" in s or "U PAN" in s or "UPANEL" in s: return "u_panel"
    if "CIRCULAR" in s or "TUBELAR" in s or "TUBULAR" in s: return "circular"
    if re.search(r"\b4[\s-]*PAN", s): return "four_panel"
    if "SINGLE LOOP" in s: return "single_loop"
    if "2 LOOP" in s or "DOUBLE LOOP" in s: return "two_loop"
    return "other"

# ── A. the +8 vs +10 body-cut split on u_panel ────────────────────────────
print("═"*78); print("A. U-PANEL BODY CUT ALLOWANCE: is +8 or +10 the standard?"); print("═"*78)
rows = []
for r in R:
    if fam((r.get("bag_type") or {}).get("first","")) != "u_panel": continue
    ext = next((d["vals"] for d in r["dims"] if d["marker"]=="EXTERNAL"), None)
    if not ext or len(ext)<3: continue
    L,W,H = ext
    b = next((c for c in r["components"] if "BODY" in U(c["name"])), None)
    s = next((c for c in r["components"] if U(c["name"]).startswith("SIDE")), None)
    if not b: continue
    cw, cc = N(b["width"]), N(b["cut"])
    if cw is None or cc is None: continue
    rows.append({
        "file": r["file"], "sheet": r["sheet"],
        "cust": U((r.get("customer") or {}).get("first","")),
        "ref":  U((r.get("ref_no") or {}).get("first","")),
        "bw": round(cw-W,1), "bc": round(cc-(2*H+L),1),
        "sw": round(N(s["width"])-L,1) if s and N(s["width"]) else None,
        "sc": round(N(s["cut"])-H,1)   if s and N(s["cut"])   else None,
    })
cnt = collections.Counter(x["bc"] for x in rows)
print(f"  n={len(rows)}  body cut residual (cut - 2H - L):")
for k,v in cnt.most_common(8): print(f"     +{k:<6} x{v:3d}  ({100*v/len(rows):.0f}%)")
print("\n  is the choice per-customer?  (customers with >=3 u-panel sheets)")
bycust = collections.defaultdict(list)
for x in rows: bycust[x["cust"]].append(x["bc"])
for c,v in sorted(bycust.items(), key=lambda kv:-len(kv[1]))[:10]:
    if len(v)>=3:
        print(f"     {c[:38]:38s} n={len(v):3d}  values={sorted(collections.Counter(v).items())}")
print("\n  body-width residual:", collections.Counter(x["bw"] for x in rows).most_common(5))
print("  side-width residual:", collections.Counter(x["sw"] for x in rows if x["sw"] is not None).most_common(5))
print("  side-cut   residual:", collections.Counter(x["sc"] for x in rows if x["sc"] is not None).most_common(5))

# ── B. GSM catalogue actually used, by family ─────────────────────────────
print("\n"+"═"*78); print("B. BODY GSM VALUES ACTUALLY WOVEN, BY FAMILY"); print("═"*78)
g = collections.defaultdict(collections.Counter)
for r in R:
    f = fam((r.get("bag_type") or {}).get("first",""))
    b = next((c for c in r["components"] if "BODY" in U(c["name"])), None)
    if b and N(b["gsm"]): g[f][int(N(b["gsm"]))] += 1
for f in ["u_panel","circular","baffle","four_panel"]:
    if f in g:
        vals = sorted(g[f].items())
        print(f"  {f:12s} n={sum(g[f].values()):4d}  {[f'{k}x{v}' for k,v in vals]}")

# ── C. missing SWL / SF / target ──────────────────────────────────────────
print("\n"+"═"*78); print("C. WHAT THE ORDER ACTUALLY SUPPLIES"); print("═"*78)
tot=len(R); miss=collections.Counter()
for r in R:
    for k in ["swl","sf","bag_wt","customer","printing","liner","doc","packing"]:
        v=(r.get(k) or {}).get("first","")
        if not str(v).strip() or U(v) in ("NA","N/A","-","0"): miss[k]+=1
for k,v in miss.most_common():
    print(f"  {k:10s} absent/NA on {v:4d}/{tot} = {100*v/tot:5.1f}%")

# ── D. same spec -> different BOM?  (the 'experience' signal) ──────────────
print("\n"+"═"*78); print("D. SAME (family, ext dims, SWL, SF) -> DIFFERENT BODY GSM?"); print("═"*78)
key = collections.defaultdict(list)
for r in R:
    ext = next((d["vals"] for d in r["dims"] if d["marker"]=="EXTERNAL"), None)
    if not ext or len(ext)<3: continue
    b = next((c for c in r["components"] if "BODY" in U(c["name"])), None)
    if not b or not N(b["gsm"]): continue
    k=(fam((r.get("bag_type") or {}).get("first","")), tuple(ext),
       U((r.get("swl") or {}).get("first","")), U((r.get("sf") or {}).get("first","")))
    key[k].append((int(N(b["gsm"])), U((r.get("customer") or {}).get("first",""))[:22], r["sheet"][:20]))
multi = {k:v for k,v in key.items() if len({x[0] for x in v})>1}
print(f"  spec groups with >1 sheet: {sum(1 for v in key.values() if len(v)>1)}")
print(f"  of those, groups where BODY GSM DIFFERS: {len(multi)}")
for k,v in sorted(multi.items(), key=lambda kv:-len(kv[1]))[:10]:
    print(f"     {k[0]:10s} {k[1]} SWL={k[2][:9]:9s} SF={k[3][:5]:5s} -> {sorted({x[0] for x in v})}")
    for x in v[:4]: print(f"          {x[0]:4d} gsm   {x[1]:22s} {x[2]}")

# ── E. loop GPM / belt width actually used ────────────────────────────────
print("\n"+"═"*78); print("E. LOOP BELT: width x GPM combinations used"); print("═"*78)
lb = collections.Counter()
for r in R:
    lp = next((c for c in r["components"] if U(c["name"]) in ("LOOP","LOOPS")), None)
    if not lp: continue
    w, gp = U(lp["width"]), N(lp["gsm"])
    if w and gp: lb[(w, int(gp))] += 1
for k,v in lb.most_common(22): print(f"  {v:4d}  belt {k[0]:12s} @ {k[1]} g/m")

# ── F. stitching weight vs bag height ─────────────────────────────────────
print("\n"+"═"*78); print("F. STITCHING (YARN) WEIGHT — is it 0.45 x H ?"); print("═"*78)
st=[]
for r in R:
    ext = next((d["vals"] for d in r["dims"] if d["marker"]=="EXTERNAL"), None)
    s = next((c for c in r["components"] if U(c["name"])=="STITCHING"), None)
    if ext and len(ext)>=3 and s and s["wt"]:
        st.append((ext[2], s["wt"], s["wt"]/ext[2]))
if st:
    ratios=sorted(x[2] for x in st)
    print(f"  n={len(st)}  yarn_g / ext_H : median {statistics.median(ratios):.3f}  "
          f"p10 {ratios[int(.1*len(ratios))]:.3f}  p90 {ratios[int(.9*len(ratios))]:.3f}")
    print(f"  distinct yarn weights used: {sorted(collections.Counter(round(x[1]) for x in st).items())[:18]}")
