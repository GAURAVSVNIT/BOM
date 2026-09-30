# -*- coding: utf-8 -*-
"""Honest version: u_panel only (where the geometry proxy is correct), and
   non-panel mass taken from the REAL non-panel components, not from a residual."""
import json, statistics, collections

P = r"C:\Users\Nikhil1616\Desktop\BOM\bom_extracted_dataset_corrected.json"
recs = json.load(open(P, encoding="utf-8"))
PANEL = {"BODY PANEL", "SIDE PANEL"}

rows = []
for r in recs:
    if r.get("bag_type") != "u_panel":
        continue
    comps = r.get("components", [])
    body = next((c for c in comps if c.get("canonical_name") == "BODY PANEL"), None)
    if not body or not body.get("gsm_area"):
        continue
    L, W, H = r.get("ext_L"), r.get("ext_W"), r.get("ext_H")
    if not all(isinstance(x, (int, float)) and x > 0 for x in (L, W, H)):
        continue
    # non-panel mass measured directly from the sheet's own non-panel lines
    non_panel = sum(c.get("weight_g") or 0 for c in comps
                    if c.get("canonical_name") not in PANEL)
    # panel area actually cut on this sheet (from the sheet's own widths/cuts)
    panel_area = sum((c.get("width_cm") or 0) * (c.get("cut_cm") or 0) * (c.get("qty") or 1) / 10000.0
                     for c in comps if c.get("canonical_name") in PANEL)
    if panel_area <= 0:
        continue
    # formula-predicted panel area (what the rule engine would cut, no leak)
    formula_area = ((W + 8) * (2 * H + L + 8) + 2 * (L + 8) * (H + 8)) / 10000.0
    rows.append(dict(swl=r.get("swl_kg"), sf=r.get("sf"), gsm=body["gsm_area"],
                     target=r.get("bag_weight_target_g"), actual=r.get("bag_weight_actual_g"),
                     non_panel=non_panel, panel_area=panel_area, formula_area=formula_area))

print(f"u_panel rows: {len(rows)}")
ar = sorted(abs(r["formula_area"] - r["panel_area"]) / r["panel_area"] * 100 for r in rows)
print(f"panel-area formula vs actual cut: median err {statistics.median(ar):.2f}%  "
      f"within5% {100*sum(1 for x in ar if x<=5)/len(ar):.1f}%")

CATALOGUE = sorted({r["gsm"] for r in rows if 60 <= r["gsm"] <= 400})
snap = lambda x: min(CATALOGUE, key=lambda c: abs(c - x))

cell = collections.defaultdict(list)
for r in rows:
    cell[(r["swl"], r["sf"])].append(r["gsm"])

def score(pairs, label):
    e = sorted(abs(p - a) / a * 100 for p, a in pairs)
    print(f"{label:56s} n={len(e):4d}  median {statistics.median(e):5.2f}%  "
          f"exact {100*sum(1 for x in e if x<1e-9)/len(e):5.1f}%  "
          f"w5% {100*sum(1 for x in e if x<=5)/len(e):5.1f}%  "
          f"w10% {100*sum(1 for x in e if x<=10)/len(e):5.1f}%")

A, F = [], []
for r in rows:
    k = (r["swl"], r["sf"])
    o = cell[k].copy(); o.remove(r["gsm"])
    if o:
        A.append((statistics.median(o), r["gsm"]))
    t = r["target"]; a = r["actual"]
    if not (isinstance(t,(int,float)) and t>100 and isinstance(a,(int,float)) and a>100):
        continue
    if abs(t-a)/a > 0.30:
        continue
    # NO LEAK: formula area, real non-panel mass, customer's target
    pred = (t - r["non_panel"]) / r["formula_area"]
    if pred > 0:
        F.append((snap(pred), r["gsm"]))

score(A, "A) chart cell median (SWL,SF), LOO  [u_panel]")
score(F, "F) (target - non_panel_mass) / FORMULA area -> snap")
