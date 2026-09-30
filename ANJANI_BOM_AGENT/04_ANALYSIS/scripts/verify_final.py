# -*- coding: utf-8 -*-
import json, re, os, collections, statistics
OUT = r"C:\Users\NIKHIL~1\AppData\Local\Temp\claude\C--Users-Nikhil1616-Desktop-BOM\2c1e7519-df0c-427f-bb17-3b433db17f20\scratchpad"
R = json.load(open(os.path.join(OUT,"corpus_allthings.json"), encoding="utf-8"))
def N(s):
    if s is None: return None
    if isinstance(s,(int,float)): return float(s)
    m=re.search(r"-?\d+(?:\.\d+)?", str(s).replace(",",""));  return float(m.group()) if m else None
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

print("="*76); print("A. YARN = coefficient x EXTERNAL HEIGHT   (engineer's new rule)"); print("="*76)
CO = {"u_panel":0.45,"four_panel":0.65,"baffle":0.70,"circular":0.50,"single_loop":0.25,"two_loop":0.30}
for f,c in CO.items():
    errs=[]
    for r in R:
        if fam((r.get("bag_type") or {}).get("first","")) != f: continue
        ext=next((d["vals"] for d in r["dims"] if d["marker"]=="EXTERNAL"),None)
        s=next((x for x in r["components"] if U(x["name"])=="STITCHING"),None)
        if ext and len(ext)>=3 and s and s["wt"] and ext[2]>0:
            errs.append(abs(c*ext[2]-s["wt"])/s["wt"]*100)
    if len(errs)>=5:
        errs.sort()
        print(f"  {f:12s} coeff {c}  n={len(errs):4d}  median err {statistics.median(errs):5.1f}%  "
              f"w10% {100*sum(1 for e in errs if e<=10)/len(errs):4.0f}%  w20% {100*sum(1 for e in errs if e<=20)/len(errs):4.0f}%")

print("\n"+"="*76); print("B. U-PANEL BODY CUT = 2H + L + 8   (engineer's ruling; data said +10)"); print("="*76)
c=collections.Counter()
for r in R:
    if fam((r.get("bag_type") or {}).get("first","")) != "u_panel": continue
    ext=next((d["vals"] for d in r["dims"] if d["marker"]=="EXTERNAL"),None)
    b=next((x for x in r["components"] if "BODY" in U(x["name"])),None)
    if ext and len(ext)>=3 and b and N(b["cut"]): c[round(N(b["cut"])-(2*ext[2]+ext[0]),1)]+=1
t=sum(c.values())
print(f"  n={t}   +8: {100*c.get(8.0,0)/t:.1f}%   +10: {100*c.get(10.0,0)/t:.1f}%")
print(f"  ENGINEER RULES +8. Historical sheets used +10 on {c.get(10.0,0)} of {t}.")
print(f"  Weight impact at 150 GSM, 93cm width: 2cm x 93 x 150/10000 = {2*93*150/10000:.2f} g  (~0.3% of an 880 g bag)")

print("\n"+"="*76); print("C. LAMINATION COATING TABLE   base GSM -> coating"); print("="*76)
BANDS=[(50,65,15),(66,130,20),(131,150,25),(151,210,30),(211,240,35)]
def coat(base):
    for lo,hi,c_ in BANDS:
        if lo<=base<=hi: return c_
    return None
hit=miss=0; ex=[]
for r in R:
    for x in r["components"]:
        m=re.match(r"^\s*(\d+)\s*\+\s*(\d+)\s*(?:GSM|LAMINATED|LAMI)?", U(x["remark"]))
        if not m: continue
        base,c_=int(m.group(1)),int(m.group(2))
        p=coat(base)
        if p is None: continue
        if p==c_: hit+=1
        else:
            miss+=1
            if len(ex)<10: ex.append((base,c_,p))
tot=hit+miss
print(f"  n={tot}  exact {100*hit/max(tot,1):.1f}%")
print("  mismatches (base, actual coating, table says):", ex[:10])

print("\n"+"="*76); print("D. TOP PANEL:  U+2 -> (L+8)x(W+8)   |   4-panel -> (L+10)x(W+10)"); print("="*76)
for f,add in (("u_panel",8),("four_panel",10),("circular",10),("baffle",8)):
    res=collections.Counter()
    for r in R:
        if fam((r.get("bag_type") or {}).get("first","")) != f: continue
        ext=next((d["vals"] for d in r["dims"] if d["marker"]=="EXTERNAL"),None)
        tp=next((x for x in r["components"] if "TOP PAN" in U(x["name"])),None)
        if ext and len(ext)>=3 and tp and N(tp["width"]): res[round(N(tp["width"])-ext[0],1)]+=1
    t2=sum(res.values())
    if t2>=5:
        print(f"  {f:12s} rule +{add}  n={t2:3d}  match {100*res.get(float(add),0)/t2:5.1f}%   top={res.most_common(4)}")

print("\n"+"="*76); print("E. BOTTOM GSM == BODY GSM ?"); print("="*76)
same=diff=0
for r in R:
    b=next((x for x in r["components"] if U(x["name"])=="BODY PANEL"),None)
    bo=next((x for x in r["components"] if "BOTTOM PAN" in U(x["name"])),None)
    if b and bo and N(b["gsm"]) and N(bo["gsm"]):
        if abs(N(b["gsm"])-N(bo["gsm"]))<1: same+=1
        else: diff+=1
print(f"  same {same}  different {diff}   ->  {100*same/max(same+diff,1):.1f}% identical")
