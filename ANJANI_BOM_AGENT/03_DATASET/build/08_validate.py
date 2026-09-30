# -*- coding: utf-8 -*-
"""
08_validate.py — quality gates on the finished dataset.

  1. RENDERER REPLAY  BuildSpec_gold -> renderer -> compare to PhysicalBOM_gold.
                      This is the honest measure of how good the geometry rules
                      are, and it is what phase 2 of the build plan must beat.
  2. LEAKAGE          no fingerprint in two splits; no identical input text.
  3. SCHEMA           every adapter row has the required keys and legal enums.
  4. FIREWALL         no BuildSpec-only field appears in any OrderSpec.
"""
import os, sys, json, math, hashlib, collections, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rules as R
from renderer import render

from _bompaths import ROOT, OUT, GOLD  # portable paths; see _bompaths.py
L = lambda p: [json.loads(x) for x in open(p, encoding="utf-8")]
order = L(os.path.join(GOLD, "order_spec.jsonl"))
build = L(os.path.join(GOLD, "build_spec.jsonl"))
phys = L(os.path.join(GOLD, "physical_bom.jsonl"))

def V(o, k):
    f = o.get(k)
    return f.get("value") if isinstance(f, dict) else None

def dims(o, tag):
    d = [V(o, f"{tag}_{a}_cm") for a in ("L", "W", "H")]
    return d if all(x is not None for x in d) else None

report = {}

# ══════════ 1. renderer replay ══════════════════════════════════════════
print("=" * 78); print("1. RENDERER REPLAY  — BuildSpec_gold vs what was actually cut")
print("=" * 78)
tot_err, comp_hits, comp_tot = [], collections.Counter(), collections.Counter()
per_fam = collections.defaultdict(list)
n_rendered = 0
for i, b in enumerate(build):
    o, p = order[i], phys[i]
    ext, itn = dims(o, "ext"), dims(o, "int")
    clean = {k: v for k, v in b.items() if not k.startswith("_")}
    lines, total = render(clean, ext, itn)
    if not total or not p["grand_total_g"]:
        continue
    n_rendered += 1
    err = abs(total - p["grand_total_g"]) / p["grand_total_g"] * 100
    tot_err.append(err)
    per_fam[b["family"]].append(err)
    # component-level geometry agreement
    actual = {c["canonical"]: c for c in p["components"] if c["canonical"]}
    for ln in lines:
        nm = ln["name"]
        if nm not in actual:
            continue
        a = actual[nm]
        if ln.get("width_cm") and a.get("width_cm"):
            comp_tot[nm + ".width"] += 1
            if abs(ln["width_cm"] - a["width_cm"]) <= 2:
                comp_hits[nm + ".width"] += 1
        if ln.get("cut_cm") and a.get("cut_cm"):
            comp_tot[nm + ".cut"] += 1
            if abs(ln["cut_cm"] - a["cut_cm"]) <= 2:
                comp_hits[nm + ".cut"] += 1

tot_err.sort()
print(f"  sheets rendered            {n_rendered} / {len(build)}")
print(f"  median grand-total error   {statistics.median(tot_err):.2f}%")
print(f"  within  2%                 {100*sum(1 for e in tot_err if e<=2)/len(tot_err):.1f}%")
print(f"  within  5%                 {100*sum(1 for e in tot_err if e<=5)/len(tot_err):.1f}%")
print(f"  within 10%                 {100*sum(1 for e in tot_err if e<=10)/len(tot_err):.1f}%")
print("\n  by family (median error, n):")
for f, v in sorted(per_fam.items(), key=lambda kv: -len(kv[1])):
    if len(v) >= 4:
        print(f"     {f:20s} {statistics.median(v):6.2f}%   n={len(v)}")
print("\n  component geometry within 2 cm:")
for k in sorted(comp_tot, key=lambda x: -comp_tot[x]):
    if comp_tot[k] >= 10:
        print(f"     {k:26s} {100*comp_hits[k]/comp_tot[k]:5.1f}%   n={comp_tot[k]}")
report["renderer_replay"] = {
    "n": n_rendered, "median_pct": round(statistics.median(tot_err), 3),
    "within_2pct": round(100*sum(1 for e in tot_err if e <= 2)/len(tot_err), 1),
    "within_5pct": round(100*sum(1 for e in tot_err if e <= 5)/len(tot_err), 1),
    "within_10pct": round(100*sum(1 for e in tot_err if e <= 10)/len(tot_err), 1),
    "component_geometry": {k: round(100*comp_hits[k]/comp_tot[k], 1)
                           for k in comp_tot if comp_tot[k] >= 10},
}

# ══════════ 2. leakage ══════════════════════════════════════════════════
print("\n" + "=" * 78); print("2. LEAKAGE"); print("=" * 78)
leak_ok = True
for ad in ("adapter_a", "adapter_b"):
    fps, texts = {}, {}
    for s in ("train", "val", "test"):
        p = os.path.join(OUT, ad, s + ".jsonl")
        if not os.path.exists(p):
            continue
        rows = L(p)
        fps[s] = {r["fingerprint"] for r in rows}
        # hash the WHOLE input — a 600-char prefix is identical for every
        # sparse OrderSpec and reports overlap that does not exist
        texts[s] = {hashlib.sha1(json.dumps(r["input"], sort_keys=True,
                                            default=str).encode()).hexdigest()
                    for r in rows}
    bad = []
    for a in fps:
        for b_ in fps:
            if a < b_:
                if fps[a] & fps[b_]:
                    bad.append(f"fingerprint {a}/{b_}: {len(fps[a] & fps[b_])}")
                if texts[a] & texts[b_]:
                    bad.append(f"identical input {a}/{b_}: {len(texts[a] & texts[b_])}")
    print(f"  {ad:12s} {'PASS — no overlap' if not bad else 'FAIL ' + str(bad)}")
    leak_ok &= not bad
report["leakage_clean"] = leak_ok

# ══════════ 3. schema ═══════════════════════════════════════════════════
print("\n" + "=" * 78); print("3. SCHEMA"); print("=" * 78)
issues = collections.Counter()
n_rows = 0
for ad, req in (("adapter_a", ("system", "input", "output", "split", "id", "fingerprint")),
                ("adapter_b", ("system", "input", "output", "split", "id", "fingerprint"))):
    for s in ("train", "val", "test"):
        p = os.path.join(OUT, ad, s + ".jsonl")
        if not os.path.exists(p):
            continue
        for r in L(p):
            n_rows += 1
            for k in req:
                if k not in r:
                    issues[f"{ad}.missing.{k}"] += 1
            if ad == "adapter_a":
                if not isinstance(r["input"], str) or len(r["input"]) < 10:
                    issues["adapter_a.input_too_short"] += 1
                for k, v in r["output"].items():
                    if isinstance(v, dict) and v.get("state") not in \
                            (None, "provided", "not_specified", "derived", "repaired"):
                        issues["adapter_a.bad_state"] += 1
            else:
                out = r["output"]
                bs = out.get("build_spec", out)
                fam = bs.get("family")
                if fam and fam not in R.ENUMS["family"]:
                    issues["adapter_b.bad_family"] += 1
                lt = bs.get("loop_type")
                if lt and lt not in R.ENUMS["loop_type"]:
                    issues["adapter_b.bad_loop_type"] += 1
                g = bs.get("body_gsm")
                if g and g not in R.GSM_CATALOGUE:
                    issues["adapter_b.gsm_off_catalogue"] += 1
print(f"  rows checked  {n_rows}")
if issues:
    for k, v in issues.most_common():
        print(f"   {v:5d}  {k}")
else:
    print("  PASS — no schema violations")
report["schema_issues"] = dict(issues)

# ══════════ 4. firewall ═════════════════════════════════════════════════
print("\n" + "=" * 78); print("4. FIREWALL"); print("=" * 78)
BUILD_ONLY = {"body_gsm", "belt_gpm", "yarn_weight_g", "baffle_gsm", "bottom_gsm",
              "top_gsm", "spout_gsm", "dust_proof", "fold_spec", "stitch_spec",
              "has_baffle", "has_felt", "body_laminated", "family", "loop_type"}
breaches = set()
for o in order:
    breaches |= (set(o.keys()) & BUILD_ONLY)
for p in [os.path.join(OUT, "adapter_a", s + ".jsonl") for s in ("train", "val", "test")]:
    if os.path.exists(p):
        for r in L(p):
            breaches |= (set(r["output"].keys()) & BUILD_ONLY)
print(f"  {'PASS — no BuildSpec field reaches OrderSpec' if not breaches else 'FAIL: ' + str(breaches)}")
report["firewall_clean"] = not breaches

json.dump(report, open(os.path.join(OUT, "validation.json"), "w", encoding="utf-8"),
          indent=1, default=str)
print(f"\nwrote validation.json")
