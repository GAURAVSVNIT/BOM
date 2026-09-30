# -*- coding: utf-8 -*-
"""Is body GSM predictable from (family, SWL, SF)?  Or from the TARGET WEIGHT?"""
import json, statistics, collections

P = r"C:\Users\Nikhil1616\Desktop\BOM\bom_extracted_dataset_corrected.json"
recs = json.load(open(P, encoding="utf-8"))

rows = []
for r in recs:
    body = next((c for c in r.get("components", []) if c.get("canonical_name") == "BODY PANEL"), None)
    if not body or not body.get("gsm_area"):
        continue
    t = r.get("bag_weight_target_g")
    a = r.get("bag_weight_actual_g")
    L, W, H = r.get("ext_L"), r.get("ext_W"), r.get("ext_H")
    if not all(isinstance(x, (int, float)) and x > 0 for x in (L, W, H)):
        continue
    # rough fabric surface proxy (m^2): body + sides for u_panel-ish geometry
    area = ((W + 8) * (2 * H + L + 8) + 2 * (L + 8) * (H + 8)) / 10000.0
    rows.append(dict(fam=r.get("bag_type"), swl=r.get("swl_kg"), sf=r.get("sf"),
                     gsm=body["gsm_area"], target=t, actual=a, area=area,
                     L=L, W=W, H=H, cust=r.get("customer")))

print(f"usable rows: {len(rows)}")

def mape(pairs):
    e = [abs(p - a) / a * 100 for p, a in pairs if a]
    e.sort()
    return (statistics.median(e), 100 * sum(1 for x in e if x <= 5) / len(e),
            100 * sum(1 for x in e if x < 1e-9) / len(e), len(e))

# ---- Predictor A: median GSM of the (family, SWL, SF) cell, leave-one-out ----
cell = collections.defaultdict(list)
for r in rows:
    cell[(r["fam"], r["swl"], r["sf"])].append(r["gsm"])

A = []
for r in rows:
    k = (r["fam"], r["swl"], r["sf"])
    others = [g for g in cell[k] if g is not None]
    others = others.copy(); others.remove(r["gsm"])          # leave-one-out
    if others:
        A.append((statistics.median(others), r["gsm"]))
m, w5, ex, n = mape(A)
print(f"\nA) GSM from (family,SWL,SF) median, LOO      n={n:4d}  median err {m:5.2f}%  within5% {w5:5.1f}%  exact {ex:5.1f}%")

# ---- Predictor B: invert the weight formula from the TARGET weight ----------
# non-body mass (loops+yarn+label+accessories) ~ measured residual; use actual BOM
B = []
for r in rows:
    if not (isinstance(r["target"], (int, float)) and r["target"] > 100
            and isinstance(r["actual"], (int, float)) and r["actual"] > 100):
        continue
    if abs(r["target"] - r["actual"]) / r["actual"] > 0.30:      # drop garbage targets
        continue
    # what GSM would make the panels weigh (target - non_panel_mass)?
    non_panel = r["actual"] - r["gsm"] * r["area"]
    if non_panel < 0 or r["target"] - non_panel <= 0:
        continue
    pred = (r["target"] - non_panel) / r["area"]
    B.append((pred, r["gsm"]))
m, w5, ex, n = mape(B)
print(f"B) GSM inverted from TARGET WEIGHT + geometry n={n:4d}  median err {m:5.2f}%  within5% {w5:5.1f}%  exact {ex:5.1f}%")

# ---- Predictor C: same customer + same family, LOO --------------------------
cc = collections.defaultdict(list)
for r in rows:
    cc[(r["cust"], r["fam"])].append(r["gsm"])
C = []
for r in rows:
    k = (r["cust"], r["fam"])
    o = cc[k].copy(); o.remove(r["gsm"])
    if o:
        C.append((statistics.median(o), r["gsm"]))
m, w5, ex, n = mape(C)
print(f"C) GSM from same CUSTOMER+family median, LOO  n={n:4d}  median err {m:5.2f}%  within5% {w5:5.1f}%  exact {ex:5.1f}%")

# ---- How often is target weight actually available? ------------------------
have_t = sum(1 for r in rows if isinstance(r["target"], (int, float)) and r["target"] > 100
             and isinstance(r["actual"], (int, float)) and r["actual"] > 100
             and abs(r["target"] - r["actual"]) / r["actual"] <= 0.30)
print(f"\nrows with a usable target weight: {have_t}/{len(rows)} = {100*have_t/len(rows):.1f}%")

swl_missing = sum(1 for r in rows if not r["swl"])
print(f"rows with NO SWL at all         : {swl_missing}/{len(rows)} = {100*swl_missing/len(rows):.1f}%")

# ---- Does the actual BOM land on the target? (is target a constraint?) -----
g = []
for r in rows:
    if isinstance(r["target"], (int, float)) and r["target"] > 100 and isinstance(r["actual"], (int, float)) and r["actual"] > 100:
        d = abs(r["actual"] - r["target"]) / r["target"] * 100
        if d < 50:
            g.append(d)
g.sort()
print(f"\nBOM total vs stated target (n={len(g)}): median {statistics.median(g):.2f}%  "
      f"within1% {100*sum(1 for x in g if x<=1)/len(g):.0f}%  "
      f"within2% {100*sum(1 for x in g if x<=2)/len(g):.0f}%  "
      f"within5% {100*sum(1 for x in g if x<=5)/len(g):.0f}%")
