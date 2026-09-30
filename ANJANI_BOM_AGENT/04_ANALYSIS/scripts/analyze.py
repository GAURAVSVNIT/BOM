# -*- coding: utf-8 -*-
import json, statistics, collections

P = r"C:\Users\Nikhil1616\Desktop\BOM\bom_extracted_dataset_corrected.json"
data = json.load(open(P, encoding="utf-8"))
recs = data if isinstance(data, list) else data.get("boms", data.get("records", []))
print("RECORDS:", len(recs))

# ---- 1. feasibility check on the user's query -------------------------------
print("\n=== 1. USER QUERY FEASIBILITY (85x85x85, 4 corner loop, yarn 40, label 2) ===")
for gsm in (110, 120, 130, 140, 150, 160):
    body = gsm * 93 * 263 / 10000
    side = gsm * 93 * 93 / 10000 * 2
    loop = 35 * 1.50 * 4
    tot = body + side + loop + 40 + 2
    print(f"  GSM {gsm}: body {body:7.2f} + side {side:7.2f} + loop {loop:6.2f} + 42 = {tot:8.2f} g")

# ---- 2. how many numbers does a BOM contain --------------------------------
print("\n=== 2. NUMERIC CELLS PER BOM (component table only) ===")
ncomp = [len(r.get("components", [])) for r in recs]
print(f"  components/BOM: median {statistics.median(ncomp):.0f}  mean {statistics.mean(ncomp):.1f}  max {max(ncomp)}")
# each component row carries gsm, width, cut, qty, weight = 5 numbers
print(f"  numeric cells in component table alone: median {5*statistics.median(ncomp):.0f}")
nonint = 0; tot_w = 0
for r in recs:
    for c in r.get("components", []):
        w = c.get("weight_g")
        if isinstance(w, (int, float)):
            tot_w += 1
            if abs(w - round(w)) > 1e-9:
                nonint += 1
print(f"  component weights that are NOT whole numbers: {nonint}/{tot_w} = {100*nonint/max(tot_w,1):.1f}%")

# ---- 3. compounding error math ---------------------------------------------
print("\n=== 3. COMPOUNDING ERROR (document correct only if EVERY number correct) ===")
for n in (55, 90):
    for p in (0.99, 0.995, 0.999, 0.9999):
        print(f"  {n} numbers @ {p:.4f} per-number accuracy -> document accuracy {100*p**n:6.2f}%")
    print()

# ---- 4. which fields are "engineer decisions" not in a typical query --------
print("\n=== 4. FIELD COVERAGE ACROSS CORPUS (candidate BuildSpec targets) ===")
fields = ["bag_type","swl_kg","sf","ext_L","ext_W","ext_H","int_L","int_W","int_H",
          "body_laminated","double_layer","fabric_color","top_type","has_fs_spout",
          "fs_spout_w_cm","fs_spout_h_cm","has_ds_spout","ds_spout_w_cm","ds_spout_h_cm",
          "ds_closure","has_baffle","has_liner","liner_micron","loop_qty","loop_width_mm",
          "loop_LL_cm","loop_SL_cm","loop_color","printing_sides","has_doc_pocket",
          "has_ddp","has_stevedore","bag_weight_target_g","bag_weight_actual_g"]
for f in fields:
    present = sum(1 for r in recs if r.get(f) not in (None, "", "None"))
    print(f"  {f:26s} {present:4d}/{len(recs)}  {100*present/len(recs):5.1f}%")

# ---- 5. target vs actual weight --------------------------------------------
print("\n=== 5. TARGET vs ACTUAL BAG WEIGHT ===")
gaps = []
for r in recs:
    t, a = r.get("bag_weight_target_g"), r.get("bag_weight_actual_g")
    if isinstance(t,(int,float)) and isinstance(a,(int,float)) and t>0 and a>0:
        gaps.append(abs(a-t)/t*100)
if gaps:
    gaps.sort()
    print(f"  n={len(gaps)}  median {statistics.median(gaps):.2f}%  "
          f"p80 {gaps[int(.8*len(gaps))]:.2f}%  p95 {gaps[int(.95*len(gaps))]:.2f}%  max {gaps[-1]:.1f}%")
    print(f"  within 2%: {100*sum(1 for g in gaps if g<=2)/len(gaps):.1f}%   "
          f"within 5%: {100*sum(1 for g in gaps if g<=5)/len(gaps):.1f}%")

# ---- 6. component-set variety (how much is 'which parts' vs 'what numbers') --
print("\n=== 6. COMPONENT VOCABULARY ===")
cnt = collections.Counter()
for r in recs:
    for c in r.get("components", []):
        cnt[c.get("canonical_name")] += 1
for name, n in cnt.most_common(40):
    print(f"  {str(name):22s} {n:5d}   ({100*n/len(recs):5.1f}% of BOMs)")

# ---- 7. bag family distribution --------------------------------------------
print("\n=== 7. BAG FAMILY DISTRIBUTION ===")
fam = collections.Counter(r.get("bag_type") for r in recs)
for k, v in fam.most_common():
    print(f"  {str(k):22s} {v:4d}")

# ---- 8. GSM spread within one (family, swl, sf) cell -> 'experience' signal --
print("\n=== 8. GSM CHOICE SPREAD WITHIN THE SAME (family, SWL, SF) ===")
buckets = collections.defaultdict(list)
for r in recs:
    body = next((c for c in r.get("components",[]) if c.get("canonical_name")=="BODY PANEL"), None)
    if body and body.get("gsm_area") and r.get("swl_kg") and r.get("sf") and r.get("bag_type"):
        buckets[(r["bag_type"], r["swl_kg"], r["sf"])].append(body["gsm_area"])
multi = {k: v for k, v in buckets.items() if len(v) >= 5}
print(f"  cells with >=5 samples: {len(multi)}")
spreads = []
for k, v in sorted(multi.items(), key=lambda x: -len(x[1]))[:12]:
    u = sorted(set(v))
    spreads.append((max(v)-min(v))/min(v)*100)
    print(f"  {str(k):34s} n={len(v):3d}  distinct GSM={u}")
if spreads:
    print(f"  median within-cell GSM spread: {statistics.median(spreads):.1f}%")
