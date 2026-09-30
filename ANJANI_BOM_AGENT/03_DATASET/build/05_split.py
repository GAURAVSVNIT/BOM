# -*- coding: utf-8 -*-
"""
05_split.py — collapse duplicates, then split by SPEC FINGERPRINT (never by row).

The previous project split by workbook — the right instinct — and still leaked
49% of validation rows verbatim, because the same enquiry file exists under
several paths. Fingerprint grouping is what actually fixes it.
"""
import os, sys, json, random, collections, hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _bompaths import ROOT, OUT, GOLD  # noqa: E402  (portable paths; see _bompaths.py)
random.seed(20260826)


def load(name):
    return [json.loads(l) for l in
            open(os.path.join(GOLD, name + ".jsonl"), encoding="utf-8")]


order = load("order_spec"); build = load("build_spec")
phys = load("physical_bom"); clar = load("clarification")
by_id = {o["_id"]: i for i, o in enumerate(order)}

# ── 1. collapse exact duplicate (OrderSpec, BuildSpec) pairs ────────────
def sig(i):
    o, b = order[i], build[i]
    ov = tuple(sorted((k, str(v.get("value"))) for k, v in o.items()
                      if isinstance(v, dict) and "state" in v))
    bv = tuple(sorted((k, str(v)) for k, v in b.items() if not k.startswith("_")))
    return hashlib.sha1(str((ov, bv)).encode()).hexdigest()


seen, keep = {}, []
for i in range(len(order)):
    s = sig(i)
    if s in seen:
        continue
    seen[s] = i
    keep.append(i)
print(f"records                 {len(order)}")
print(f"after collapsing exact duplicate pairs   {len(keep)}"
      f"   (dropped {len(order)-len(keep)})")

# ── 2. group by fingerprint, stratify by family ─────────────────────────
groups = collections.defaultdict(list)
for i in keep:
    groups[order[i]["_fingerprint"]].append(i)
print(f"fingerprint groups      {len(groups)}")

fam_of = {}
for fp, idxs in groups.items():
    fams = collections.Counter(build[i]["family"] for i in idxs)
    fam_of[fp] = fams.most_common(1)[0][0]

by_fam = collections.defaultdict(list)
for fp in groups:
    by_fam[fam_of[fp]].append(fp)

# issue #4: the old rule sent EVERY family with < 4 fingerprint groups entirely
# to train, so platten / container_liner / tunnel / hood had zero val+test
# coverage and could never be evaluated. New rule: families with 2-3 groups
# still contribute one held-out group (alternating val/test so both sides see
# the family); only genuine singletons stay train-only. Whole groups move, so
# zero-leakage is preserved.
split = {}
degraded = []                      # families whose eval coverage is below target
for fi, fam in enumerate(sorted(by_fam)):
    fps = sorted(by_fam[fam])
    random.shuffle(fps)
    n = len(fps)
    if n >= 4:
        n_test = max(1, round(n * 0.15))
        n_val = max(1, round(n * 0.15))
    elif n in (2, 3):
        n_test, n_val = ((1, 0) if fi % 2 == 0 else (0, 1))
        degraded.append((fam, n, "test" if n_test else "val"))
    else:                          # n == 1 — cannot split without leaking
        n_test = n_val = 0
        degraded.append((fam, n, "train-only"))
    for j, fp in enumerate(fps):
        split[fp] = "test" if j < n_test else ("val" if j < n_test + n_val else "train")

if degraded:
    print("\n  DEGRADED EVAL COVERAGE (too few fingerprint groups for a 15% split):")
    for fam, n, where in degraded:
        print(f"     {fam:20s} {n} group(s)  -> {where}")

buckets = collections.defaultdict(list)
for fp, idxs in groups.items():
    for i in idxs:
        buckets[split[fp]].append(i)

print("\nSPLIT (fingerprint groups, stratified by family)")
for s in ("train", "val", "test"):
    fams = collections.Counter(build[i]["family"] for i in buckets[s])
    print(f"  {s:6s} {len(buckets[s]):4d} records  "
          f"{len({order[i]['_fingerprint'] for i in buckets[s]}):4d} groups   "
          f"{dict(fams.most_common(6))}")

# ── 3. zero-leakage assertion ───────────────────────────────────────────
fp_sets = {s: {order[i]["_fingerprint"] for i in buckets[s]} for s in buckets}
for a in ("train", "val", "test"):
    for b_ in ("train", "val", "test"):
        if a < b_:
            inter = fp_sets[a] & fp_sets[b_]
            assert not inter, f"LEAK between {a} and {b_}: {list(inter)[:5]}"
print("\n  ZERO-LEAKAGE TEST: PASS — no fingerprint appears in two splits")

# ── 4. also assert no identical raw_text across splits ──────────────────
txt = {s: {order[i]["raw_text"][:400] for i in buckets[s]} for s in buckets}
overlap = (txt["train"] & txt["val"]) | (txt["train"] & txt["test"])
print(f"  identical raw sheet text across splits: {len(overlap)}"
      f"  {'PASS' if not overlap else 'REVIEW'}")

json.dump({s: [order[i]["_id"] for i in buckets[s]] for s in buckets},
          open(os.path.join(OUT, "split.json"), "w", encoding="utf-8"), indent=1)
json.dump({"kept_index": keep},
          open(os.path.join(OUT, "dedupe.json"), "w", encoding="utf-8"), indent=1)
print(f"\nwrote split.json + dedupe.json")
