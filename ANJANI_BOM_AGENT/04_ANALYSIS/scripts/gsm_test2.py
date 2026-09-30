# -*- coding: utf-8 -*-
"""Combined predictor: invert target weight -> snap to catalogue GSM >= chart floor."""
import json, statistics, collections

P = r"C:\Users\Nikhil1616\Desktop\BOM\bom_extracted_dataset_corrected.json"
recs = json.load(open(P, encoding="utf-8"))

rows = []
for r in recs:
    body = next((c for c in r.get("components", []) if c.get("canonical_name") == "BODY PANEL"), None)
    if not body or not body.get("gsm_area"):
        continue
    L, W, H = r.get("ext_L"), r.get("ext_W"), r.get("ext_H")
    if not all(isinstance(x, (int, float)) and x > 0 for x in (L, W, H)):
        continue
    area = ((W + 8) * (2 * H + L + 8) + 2 * (L + 8) * (H + 8)) / 10000.0
    rows.append(dict(fam=r.get("bag_type"), swl=r.get("swl_kg"), sf=r.get("sf"),
                     gsm=body["gsm_area"], target=r.get("bag_weight_target_g"),
                     actual=r.get("bag_weight_actual_g"), area=area))

# catalogue of GSM values the plant actually weaves
CATALOGUE = sorted({r["gsm"] for r in rows if 60 <= r["gsm"] <= 400})
print(f"catalogue GSM values observed ({len(CATALOGUE)}): {[int(g) for g in CATALOGUE]}")

def snap(x):
    return min(CATALOGUE, key=lambda c: abs(c - x))

cell = collections.defaultdict(list)
for r in rows:
    cell[(r["fam"], r["swl"], r["sf"])].append(r["gsm"])

def score(pairs, label):
    e = sorted(abs(p - a) / a * 100 for p, a in pairs)
    print(f"{label:52s} n={len(e):4d}  median {statistics.median(e):5.2f}%  "
          f"exact {100*sum(1 for x in e if x < 1e-9)/len(e):5.1f}%  "
          f"within5% {100*sum(1 for x in e if x <= 5)/len(e):5.1f}%  "
          f"within10% {100*sum(1 for x in e if x <= 10)/len(e):5.1f}%")

A, D, E = [], [], []
for r in rows:
    k = (r["fam"], r["swl"], r["sf"])
    others = cell[k].copy(); others.remove(r["gsm"])
    chart = statistics.median(others) if others else None

    if chart:
        A.append((chart, r["gsm"]))

    t, a = r["target"], r["actual"]
    ok_t = (isinstance(t, (int, float)) and t > 100 and isinstance(a, (int, float))
            and a > 100 and abs(t - a) / a <= 0.30)
    if ok_t:
        non_panel = a - r["gsm"] * r["area"]
        if non_panel >= 0 and t - non_panel > 0:
            cont = (t - non_panel) / r["area"]
            D.append((snap(cont), r["gsm"]))
            # floor at the chart cell (safety), then snap
            floored = max(cont, chart * 0.92) if chart else cont
            E.append((snap(floored), r["gsm"]))

score(A, "A) chart cell median (family,SWL,SF), LOO")
score(D, "D) target-weight inversion -> SNAP to catalogue")
score(E, "E) target inversion, floored by chart -> SNAP")
