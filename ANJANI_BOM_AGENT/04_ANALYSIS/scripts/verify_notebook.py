# -*- coding: utf-8 -*-
import json, re, os, collections, statistics, math
R = json.load(open("corpus_allthings.json", encoding="utf-8"))
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
def dims(r, marker="INTERNAL"):
    return next((d["vals"] for d in r["dims"] if d["marker"]==marker), None)

print("="*78); print("A. BELT GPM = SWL x SF / (loop_qty x 35)   [notebook p.107 — resolves O3]"); print("="*78)
rows=[]
for r in R:
    swl=N((r.get("swl") or {}).get("first","")); sfs=U((r.get("sf") or {}).get("first",""))
    m=re.match(r"(\d+):", sfs)
    lp=next((c for c in r["components"] if U(c["name"]) in ("LOOP","LOOPS")), None)
    if not (swl and m and lp and N(lp["gsm"])): continue
    sf=float(m.group(1)); gpm=N(lp["gsm"])
    req = swl*sf/(4*35)
    rows.append((gpm, req, abs(gpm-req)/req*100, swl, sf))
errs=sorted(x[2] for x in rows)
print(f"  n={len(rows)}  median |actual-required|/required = {statistics.median(errs):.1f}%")
print(f"  within 15%: {100*sum(1 for e in errs if e<=15)/len(errs):.0f}%   within 25%: {100*sum(1 for e in errs if e<=25)/len(errs):.0f}%")
over = sum(1 for x in rows if x[0] >= x[1]*0.95)
print(f"  actual >= 95% of required (i.e. adequately specified): {100*over/len(rows):.0f}%")
print("  sample:", [(x[3],x[4],x[0],round(x[1],1)) for x in rows[:6]])

print("\n"+"="*78); print("B. BAFFLE PANEL WIDTH = sqrt((L/3)^2+(W/3)^2) + 7   [notebook p.59]"); print("="*78)
res=collections.Counter(); n=0
for r in R:
    if fam((r.get("bag_type") or {}).get("first","")) != "baffle": continue
    idm = dims(r,"INTERNAL") or dims(r,"EXTERNAL")
    b=next((c for c in r["components"] if U(c["name"]) in ("BAFFLE","BAFFLE FABRIC")), None)
    if not (idm and len(idm)>=3 and b and N(b["width"])): continue
    L,W,H = idm; pred = math.sqrt((L/3)**2+(W/3)**2)+7
    d = round(N(b["width"]) - pred, 0); res[d]+=1; n+=1
print(f"  n={n}  residual (actual - predicted):  {res.most_common(8)}")
if n: print(f"  within 3 cm: {100*sum(v for k,v in res.items() if abs(k)<=3)/n:.0f}%")

print("\n"+"="*78); print("C. BAFFLE CUT LENGTH = H_internal - 20   [notebook p.60]"); print("="*78)
res=collections.Counter(); n=0
for r in R:
    if fam((r.get("bag_type") or {}).get("first","")) != "baffle": continue
    idm = dims(r,"INTERNAL")
    b=next((c for c in r["components"] if U(c["name"]) in ("BAFFLE","BAFFLE FABRIC")), None)
    if not (idm and len(idm)>=3 and b and N(b["cut"])): continue
    res[round(N(b["cut"]) - (idm[2]-20),0)]+=1; n+=1
print(f"  n={n}  residual: {res.most_common(8)}")
if n: print(f"  exact: {100*res.get(0.0,0)/n:.0f}%   within 3 cm: {100*sum(v for k,v in res.items() if abs(k)<=3)/n:.0f}%")

print("\n"+"="*78); print("D. SKIRT width = W/2 + 15 + W/4 + 5 ;  length = 4W + 12   [notebook p.101]"); print("="*78)
wres=collections.Counter(); lres=collections.Counter(); n=0
for r in R:
    idm = dims(r,"INTERNAL") or dims(r,"EXTERNAL")
    s=next((c for c in r["components"] if U(c["name"]) in ("SKIRT","DUFFLE")), None)
    if not (idm and len(idm)>=3 and s and N(s["width"]) and N(s["cut"])): continue
    L,W,H = idm
    wres[round(N(s["width"]) - (W/2+15+W/4+5),0)]+=1
    lres[round(N(s["cut"]) - (4*W+12),0)]+=1
    n+=1
print(f"  n={n}")
print(f"  width  residual: {wres.most_common(6)}")
print(f"  length residual: {lres.most_common(6)}")

print("\n"+"="*78); print("E. IRIS DS WIDTH = H + D/2 + 11, rounded UP to nearest 5   [notebook p.99]"); print("="*78)
hit=miss=0; ex=[]
for r in R:
    bot=U((r.get("bottom") or {}).get("tail",""))
    if "IRIS" not in bot and "IRISH" not in bot: continue
    m=re.search(r"(\d+(?:\.\d+)?)\s*[Xx*]\s*(\d+(?:\.\d+)?)\s*CM", bot)
    if not m: continue
    D,Hh = float(m.group(1)), float(m.group(2))
    c=next((x for x in r["components"] if U(x["name"]) in ("D/S","D SPOUT","DS SPOUT","DISCHARGE SPOUT","BOTTOM SPOUT")), None)
    if not (c and N(c["width"])): continue
    raw = Hh + D/2 + 11
    pred = math.ceil(raw/5)*5
    if abs(pred-N(c["width"]))<=2.5: hit+=1
    else:
        miss+=1
        if len(ex)<6: ex.append((D,Hh,N(c["width"]),round(raw,1),pred))
tot=hit+miss
print(f"  n={tot}  within 2.5 cm: {100*hit/max(tot,1):.0f}%")
for e in ex: print(f"     D{e[0]} H{e[1]}  actual {e[2]}  raw {e[3]} -> rounded {e[4]}")

print("\n"+"="*78); print("F. BOX BAG geometry == U-PANEL geometry?   [notebook p.71]"); print("="*78)
print("  notebook example 115x140x70 (OD):")
print("    body  = (W+8) x (2H + L + 8) = 123 x 288   <- notebook says 123 x 288  MATCH")
print("    side  = (L+8) x (H+8)        = 148 x 78    <- notebook says 148 x 78   MATCH")
print("  => box bag can reuse the u_panel geometry block verbatim")

print("\n"+"="*78); print("G. TWO-PANEL (C-type) width = 2W + 12, cut = H + 12   [notebook p.74]"); print("="*78)
print("  notebook example 105x105x120 (ID): 52.5+105+52.5+12 = 222 ; 120+12 = 132")
res=collections.Counter(); n=0
for r in R:
    s=U((r.get("bag_type") or {}).get("first",""))
    if "2 PANNEL" not in s and "TWO PANNEL" not in s and "C-TYPE" not in s and "TYPE - C" not in s: continue
    idm = dims(r,"INTERNAL") or dims(r,"EXTERNAL")
    b=next((c for c in r["components"] if "BODY" in U(c["name"]) or "SIDE" in U(c["name"])), None)
    if not (idm and len(idm)>=3 and b and N(b["width"])): continue
    res[round(N(b["width"]) - (2*idm[1]+12),0)]+=1; n+=1
print(f"  corpus n={n}  residual: {res.most_common(6)}")
