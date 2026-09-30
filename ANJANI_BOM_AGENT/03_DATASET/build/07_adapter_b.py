# -*- coding: utf-8 -*-
"""
07_adapter_b.py — the CONFIGURATION dataset.  OrderSpec + retrieved + envelope -> BuildSpec

Three row types:
  base      real engineering decisions, one per sheet          (zero labelling)
  solver    a knob is perturbed, the weight gap is shown, the model must move
            it back — IN THE ENGINEER'S KNOB ORDER: belt GPM, then loop cut,
            then body GSM
  conflict  a stated GSM below the chart floor, or a target weight that cannot
            be met — correct output is a CLARIFICATION, not a build

Retrieval is leave-one-FINGERPRINT-out so a sheet can never see its own twin.
"""
import os, sys, re, json, math, random, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rules as R
from renderer import render

from _bompaths import ROOT, OUT, GOLD  # portable paths; see _bompaths.py
DEST = os.path.join(OUT, "adapter_b")
os.makedirs(DEST, exist_ok=True)
random.seed(20260826)

L = lambda n: [json.loads(x) for x in open(os.path.join(GOLD, n + ".jsonl"), encoding="utf-8")]
order, build, phys, clar = L("order_spec"), L("build_spec"), L("physical_bom"), L("clarification")
split = json.load(open(os.path.join(OUT, "split.json"), encoding="utf-8"))
which = {i: s for s, ids in split.items() for i in ids}
idx = {o["_id"]: i for i, o in enumerate(order)}


def V(o, k):
    f = o.get(k)
    return f.get("value") if isinstance(f, dict) else None


def dims(o, tag):
    d = [V(o, f"{tag}_{a}_cm") for a in ("L", "W", "H")]
    return d if all(x is not None for x in d) else None


def public_order(o):
    """The OrderSpec exactly as adapter A would hand it over."""
    return {k: v for k, v in o.items()
            if isinstance(v, dict) and "state" in v}


def envelope(o, b):
    swl, sf = V(o, "swl_kg"), V(o, "sf")
    sfn = int(str(sf).split(":")[0]) if sf else None
    lt = b["loop_type"]
    floor = R.gsm_floor(swl, sfn, lt) if (swl and sfn) else None
    band = R.belt_band(swl, sfn, lt) if (swl and sfn) else None
    req = R.required_belt_gpm(swl, sfn, b.get("loop_qty") or 4) if (swl and sfn) else None
    return {
        "gsm_floor": floor,
        "gsm_catalogue": R.GSM_CATALOGUE,
        "belt_width_mm": band[0] if band else None,
        "belt_gpm_band": [band[1], band[2]] if band else None,
        "belt_gpm_required": round(req, 1) if req else None,
        "belt_gpm_note": "design target, not a hard limit",
        "mandatory_components": R.MANDATORY.get(b["family"], []),
        "forbidden_components": R.FORBIDDEN.get(b["family"], []),
        "lamination_bands": R.LAMINATION_BANDS,
        "yarn_coefficient": R.YARN_COEFF.get(b["family"]),
        "target_factor": R.TARGET_FACTOR,
        "tolerance": R.TOLERANCE,
        "solver_knob_order": R.SOLVER_KNOBS,
        "dimension_basis": (R.GEOMETRY.get(b["family"]) or {}).get("basis", "EXTERNAL"),
    }


# ── retrieval: leave-one-fingerprint-out top-3 ──────────────────────────
def retrieve(i, k=3):
    o, b = order[i], build[i]
    e = dims(o, "ext") or dims(o, "int")
    fp = o["_fingerprint"]
    fam = b["family"]
    cand = []
    for j, ob in enumerate(order):
        if ob["_fingerprint"] == fp:
            continue
        bb = build[j]
        if bb["family"] != fam:                 # hard family filter
            continue
        e2 = dims(ob, "ext") or dims(ob, "int")
        if not e or not e2:
            continue
        geo = math.sqrt(sum((a - c) ** 2 for a, c in zip(e, e2))) / 100.0
        s1, s2 = V(o, "swl_kg"), V(ob, "swl_kg")
        swl_d = abs((s1 or 0) - (s2 or 0)) / 1000.0
        cat = sum(0.0 if b.get(f) == bb.get(f) else 1.0
                  for f in ("top_type", "bottom_type", "loop_type",
                            "has_baffle", "has_liner")) / 5.0
        score = 0.55 * geo + 0.15 * swl_d + 0.30 * cat
        cand.append((score, j))
    cand.sort()
    out = []
    for score, j in cand[:k]:
        bb = {kk: vv for kk, vv in build[j].items() if not kk.startswith("_")}
        out.append({"similarity": round(1.0 / (1.0 + score), 4),
                    "source": build[j]["_source"], "build_spec": bb,
                    "achieved_weight_g": phys[j]["grand_total_g"]})
    return out


SYSTEM_B = (
    "You are a senior FIBC bag design engineer at Anjani Interweave. You are "
    "given what the customer asked for, the three nearest bags the plant has "
    "actually built, and the rule envelope for this load. Decide every "
    "parameter needed to build the bag and return a BuildSpec JSON. "
    "You choose from closed vocabularies only: never output a width, a cut "
    "length, a weight or a price — those are computed downstream from your "
    "decisions. If the customer stated a GSM below the chart floor, honour it "
    "and flag it. Output JSON only."
)
SYSTEM_B_SOLVE = (
    "You are a senior FIBC bag design engineer at Anjani Interweave. A BuildSpec "
    "was rendered and its finished weight missed the target. Adjust it and return "
    "the corrected BuildSpec JSON. Turn the knobs in this order: first the loop "
    "gramage, then the loop cut length, then the body GSM — and only within "
    "market-standard values for the load. Output JSON only."
)

rows = collections.defaultdict(list)
agg = collections.Counter()

for i, o in enumerate(order):
    sp = which.get(o["_id"])
    if sp is None:
        continue
    b = build[i]
    p = phys[i]
    clean_b = {k: v for k, v in b.items() if not k.startswith("_")}
    env = envelope(o, b)
    ret = retrieve(i)

    # ── base row ────────────────────────────────────────────────────────
    rows[sp].append({
        "split": sp, "adapter": "B", "row_type": "base",
        "id": o["_id"] + "_base", "fingerprint": o["_fingerprint"],
        "system": SYSTEM_B,
        "input": {"order_spec": public_order(o), "retrieved": ret, "envelope": env},
        "output": clean_b,
        "meta": {"source": o["_source"], "real": True,
                 "achieved_weight_g": p["grand_total_g"],
                 "integrity_flags": p["integrity_flags"]},
    })
    agg["base_" + sp] += 1

    # ── solver-feedback rows ────────────────────────────────────────────
    ext, itn = dims(o, "ext"), dims(o, "int")
    if sp == "train" and (ext or itn) and b.get("body_gsm") and b.get("belt_gpm"):
        _, base_total = render(clean_b, ext, itn)
        # The solver target is set from the renderer's OWN baseline for the true
        # BuildSpec, not from the sheet's grand total. The renderer does not yet
        # model every component, so using the sheet total would make the gap
        # measure renderer incompleteness rather than the perturbation — and the
        # model would learn to correct for a constant offset that will not exist
        # in production. Anchoring on base_total isolates the knob.
        # No FIBC weighs under 300 g. A total below that means the renderer has
        # no geometry for this family, so the gap would be meaningless.
        if base_total and base_total >= 300:
            target = base_total * R.TARGET_FACTOR
            # knob 1: belt gpm   knob 2: loop cut   knob 3: body gsm
            perturbations = []
            gi = R.BELT_GPM_CATALOGUE
            if b["belt_gpm"] in gi:
                k = gi.index(b["belt_gpm"])
                for d in (-2, -1, 1, 2):
                    if 0 <= k + d < len(gi):
                        perturbations.append(("belt_gpm", gi[k + d]))
            fh = b.get("loop_free_height_cm") or 25
            for d in (-10, -5, 5, 10):
                if fh + d >= 15:
                    perturbations.append(("loop_free_height_cm", fh + d))
            ci = R.GSM_CATALOGUE
            if b["body_gsm"] in ci:
                k = ci.index(b["body_gsm"])
                for d in (-2, -1, 1, 2):
                    if 0 <= k + d < len(ci):
                        perturbations.append(("body_gsm", ci[k + d]))
            random.shuffle(perturbations)
            for knob, val in perturbations[:4]:
                bad = dict(clean_b)
                bad[knob] = val
                _, bad_total = render(bad, ext, itn)
                if not bad_total:
                    continue
                gap = bad_total - target
                if abs(gap) / target <= R.TOLERANCE:
                    continue          # already inside tolerance, nothing to learn
                rows["train"].append({
                    "split": "train", "adapter": "B", "row_type": "solver_feedback",
                    "id": f"{o['_id']}_solve_{knob}_{val}",
                    "fingerprint": o["_fingerprint"],
                    "system": SYSTEM_B_SOLVE,
                    "input": {"order_spec": public_order(o), "envelope": env,
                              "current_build_spec": bad,
                              "weight_feedback": {
                                  "rendered_weight_g": round(bad_total, 2),
                                  "target_weight_g": round(target, 2),
                                  "gap_g": round(gap, 2),
                                  "gap_pct": round(100 * gap / target, 2),
                                  "tolerance_pct": 2.0,
                                  "allowed_knobs": R.SOLVER_KNOBS,
                                  "knob_ranges": {
                                      "belt_gpm": env["belt_gpm_band"],
                                      "body_gsm_floor": env["gsm_floor"]}}},
                    "output": clean_b,
                    "meta": {"perturbed_knob": knob, "perturbed_to": val,
                             "correct_value": clean_b.get(knob), "generated": True},
                })
                agg["solver"] += 1

    # ── conflict rows ───────────────────────────────────────────────────
    if sp == "train":
        c = clar[i]
        gsm_conf = [x for x in c["advisory"] if x["code"] == "GSM_BELOW_CHART"]
        if gsm_conf:
            rows["train"].append({
                "split": "train", "adapter": "B", "row_type": "conflict",
                "id": o["_id"] + "_conflict_gsm",
                "fingerprint": o["_fingerprint"],
                "system": SYSTEM_B,
                "input": {"order_spec": public_order(o), "retrieved": ret,
                          "envelope": env},
                "output": {"build_spec": clean_b,
                           "clarification": {"blocking": c["blocking"],
                                             "advisory": c["advisory"],
                                             "assumptions_made": c["assumptions_made"]}},
                "meta": {"real": True,
                         "note": "customer GSM below chart floor — honour it and flag"},
            })
            agg["conflict_gsm"] += 1

# ── constructed infeasible-target conflicts ─────────────────────────────
train_ids = [i for i, o in enumerate(order) if which.get(o["_id"]) == "train"]
made = 0
for i in random.sample(train_ids, min(120, len(train_ids))):
    o, b = order[i], build[i]
    ext, itn = dims(o, "ext"), dims(o, "int")
    clean_b = {k: v for k, v in b.items() if not k.startswith("_")}
    if not (ext or itn) or not b.get("body_gsm"):
        continue
    _, tot = render(clean_b, ext, itn)
    if not tot or tot < 300:        # renderer has no geometry for this family
        continue
    o2 = json.loads(json.dumps(o))
    impossible = round(tot * random.uniform(0.62, 0.80), 1)   # far below any legal build
    o2["req_weight_g"] = {"value": impossible, "state": "provided"}
    env = envelope(o2, b)
    rows["train"].append({
        "split": "train", "adapter": "B", "row_type": "conflict_infeasible",
        "id": o["_id"] + "_conflict_weight", "fingerprint": o["_fingerprint"],
        "system": SYSTEM_B,
        "input": {"order_spec": public_order(o2), "retrieved": retrieve(i),
                  "envelope": env},
        "output": {"build_spec": clean_b,
                   "clarification": {
                       "blocking": [],
                       "advisory": [{
                           "code": "TARGET_WEIGHT_UNREACHABLE",
                           "field": "req_weight_g",
                           "question": (
                               f"A finished weight of {impossible:.0f} g is not "
                               f"achievable for this bag. The lightest build that "
                               f"clears our GSM standard weighs about {tot:.0f} g. "
                               f"Shall we proceed against the bag weight, or against "
                               f"the specified GSM?"),
                           "achievable_g": round(tot, 1),
                           "requested_g": impossible}],
                       "assumptions_made": []}},
        "meta": {"constructed": True,
                 "note": "target below any legal build — must ask, never force"},
    })
    made += 1
agg["conflict_infeasible"] = made

for s in ("train", "val", "test"):
    with open(os.path.join(DEST, s + ".jsonl"), "w", encoding="utf-8") as f:
        for r in rows[s]:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")

print("=" * 78)
print("ADAPTER B — configuration dataset")
print("=" * 78)
for k in sorted(agg):
    print(f"  {k:24s} {agg[k]}")
print()
for s in ("train", "val", "test"):
    t = collections.Counter(r["row_type"] for r in rows[s])
    print(f"  {s:6s} {len(rows[s]):5d} rows   {dict(t)}")
print(f"\n  wrote {DEST}")
