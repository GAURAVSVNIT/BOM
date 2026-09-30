"""Evaluation against the plan §10.2 ship gates. Torch-free.

    python -m bomft.cli eval --adapter a --split test
    python -m bomft.cli eval --adapter a --split eval_real --server http://127.0.0.1:8000
    python -m bomft.cli eval --adapter b --predictions preds_b.jsonl

Predictions come from one of:
  * a running vLLM server        (--server URL)
  * an in-process vLLM engine    (--engine ; needs GPU)
  * a pre-dumped JSONL file      (--predictions ; {id, output})
The metric code does not care which; it just needs {id -> predicted dict}.

Exit code is non-zero if any HARD gate fails (CI-usable).
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import re
import statistics
import sys
from functools import lru_cache
from pathlib import Path

from .paths import adapter_jsonl, eval_real_jsonl, gold_jsonl, rules_module_path


@lru_cache(maxsize=1)
def _rules():
    spec = importlib.util.spec_from_file_location("bom_rules", rules_module_path())
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _read_jsonl(p: Path) -> list[dict]:
    with p.open(encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


# ── field helpers ──────────────────────────────────────────────────────
def _val(field):
    return field.get("value") if isinstance(field, dict) else field


def _state(field):
    return field.get("state") if isinstance(field, dict) else ("provided" if field is not None else "not_specified")


NUM_FIELDS = {"ext_L_cm", "ext_W_cm", "ext_H_cm", "int_L_cm", "int_W_cm",
              "int_H_cm", "swl_kg", "fs_dia_cm", "fs_height_cm", "ds_dia_cm",
              "ds_height_cm", "liner_micron"}
ENUM_FIELDS = {"top_type", "bottom_type", "fs_closure", "ds_closure"}
BOOL_FIELDS = {"has_liner", "has_doc_pocket", "has_printing"}


def evidence_supported(value, text: str) -> bool:
    """Is `value` actually present in the source text? (plan: evidence must be a
    verbatim substring). Numbers: the digits appear, allowing kg<->g and a
    trailing .0 . Strings: case-insensitive substring, or all tokens present."""
    if value is None or text is None:
        return True
    t = text.lower()
    if isinstance(value, bool):
        return True                      # booleans are judged by F1, not evidence
    if isinstance(value, (int, float)):
        v = float(value)
        cands = {v, v / 1000.0, v * 1000.0, round(v), round(v, 1)}
        for c in cands:
            s = (str(int(c)) if float(c).is_integer() else f"{c:g}")
            if re.search(rf"(?<!\d){re.escape(s)}(?!\d)", t):
                return True
        return False
    s = str(value).strip().lower()
    if not s or s in ("open_top", "flat_bottom", "open"):
        return True                      # house defaults, not customer claims
    if s in t:
        return True
    toks = [w for w in re.split(r"[\s/_+-]+", s) if len(w) > 2]
    return bool(toks) and all(w in t for w in toks)


# ── adapter A metrics ──────────────────────────────────────────────────
def score_adapter_a(gold_rows: list[dict], preds: dict[str, dict]) -> dict:
    # hallucination (operational): the gold says the customer did NOT state field
    # k, but the model returned it state=provided with a value. This is the
    # dataset-grounded form of "asserting a value the source does not contain"
    # (plan §4.1) and needs no fragile text matching.
    # evidence_violation (strict, secondary): among fields the model marked
    # provided that carry an `evidence` span, how many spans are not a verbatim
    # substring of the source — the plan's ideal check, meaningful on eval_real.
    hall_num = hall_den = 0
    ev_num = ev_den = 0
    num_hit = num_den = 0
    enum_hit = enum_den = 0
    tp = fp = fn = 0
    missing = 0
    for r in gold_rows:
        rid = r["id"] if "id" in r else r.get("_id")
        src = r.get("input") or r.get("raw_text") or ""
        pred = preds.get(rid)
        if pred is None:
            missing += 1
            continue
        gout = r["output"] if "output" in r else r
        pout = pred.get("output", pred)
        for k, gf in gout.items():
            if not isinstance(gf, dict) or "state" not in gf:
                continue
            pf = pout.get(k, {})
            pv, ps = _val(pf), _state(pf)
            gv, gs = _val(gf), _state(gf)
            # operational hallucination: gold not_specified, pred asserts a value
            if gs == "not_specified":
                hall_den += 1
                if ps == "provided" and pv is not None:
                    hall_num += 1
            # strict evidence check, only where the model supplied a span
            if ps == "provided" and pv is not None and isinstance(pf, dict) and pf.get("evidence"):
                ev_den += 1
                if str(pf["evidence"]).strip().lower() not in src.lower():
                    ev_num += 1
            # numeric exact match on fields the gold marks provided
            if k in NUM_FIELDS and _state(gf) == "provided" and gv is not None:
                num_den += 1
                if pv is not None and abs(float(pv) - float(gv)) < 1e-6:
                    num_hit += 1
            if k in ENUM_FIELDS and _state(gf) == "provided":
                enum_den += 1
                if str(pv) == str(gv):
                    enum_hit += 1
            if k in BOOL_FIELDS:
                g_yes = (_state(gf) == "provided" and bool(gv))
                p_yes = (ps == "provided" and bool(pv))
                tp += g_yes and p_yes
                fp += p_yes and not g_yes
                fn += g_yes and not p_yes
    prec = tp / (tp + fp) if tp + fp else 1.0
    rec = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 1.0
    return {
        "n": len(gold_rows), "missing_preds": missing,
        "hallucination_rate": round(hall_num / hall_den, 4) if hall_den else 0.0,
        "evidence_violation_rate": round(ev_num / ev_den, 4) if ev_den else None,
        "numeric_exact": round(num_hit / num_den, 4) if num_den else None,
        "enum_accuracy": round(enum_hit / enum_den, 4) if enum_den else None,
        "boolean_f1": round(f1, 4),
        "_counts": {"hall": [hall_num, hall_den], "evidence": [ev_num, ev_den],
                    "num": [num_hit, num_den], "enum": [enum_hit, enum_den],
                    "bool": [tp, fp, fn]},
    }


# ── adapter B metrics ──────────────────────────────────────────────────
_HAS_FIELDS = ["has_baffle", "has_liner", "has_doc_pocket", "has_felt",
               "has_glue", "has_tabbing_tape", "has_b_lock", "has_rope",
               "has_stevedore", "has_belly_band", "has_top_band",
               "has_loop_protector", "has_extra_loop"]


def _bs(d):
    return d.get("build_spec", d) if isinstance(d, dict) else {}


def score_adapter_b(gold_rows: list[dict], preds: dict[str, dict]) -> dict:
    cat = list(_rules().GSM_CATALOGUE)
    gsm_exact = gsm_step = gsm_den = 0
    fam_hit = fam_den = 0
    f1s = []
    missing = 0
    for r in gold_rows:
        rid = r["id"] if "id" in r else r.get("_id")
        pred = preds.get(rid)
        if pred is None:
            missing += 1
            continue
        g = _bs(r["output"] if "output" in r else r)
        p = _bs(pred.get("output", pred))
        gg, pg = g.get("body_gsm"), p.get("body_gsm")
        if gg is not None:
            gsm_den += 1
            if pg == gg:
                gsm_exact += 1
            if pg in cat and gg in cat and abs(cat.index(pg) - cat.index(gg)) <= 1:
                gsm_step += 1
        if g.get("family"):
            fam_den += 1
            fam_hit += (p.get("family") == g.get("family"))
        gset = {k for k in _HAS_FIELDS if g.get(k)}
        pset = {k for k in _HAS_FIELDS if p.get(k)}
        if gset or pset:
            inter = len(gset & pset)
            prec = inter / len(pset) if pset else 1.0
            rec = inter / len(gset) if gset else 1.0
            f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 1.0)
        else:
            f1s.append(1.0)
    return {
        "n": len(gold_rows), "missing_preds": missing,
        "body_gsm_exact": round(gsm_exact / gsm_den, 4) if gsm_den else None,
        "body_gsm_within_1_step": round(gsm_step / gsm_den, 4) if gsm_den else None,
        "family_accuracy": round(fam_hit / fam_den, 4) if fam_den else None,
        "component_set_f1": round(statistics.mean(f1s), 4) if f1s else None,
    }


# ── gates (plan §10.2) ────────────────────────────────────────────────
GATES_A = [
    ("hallucination_rate", "<=", 0.02, True),
    ("numeric_exact", ">=", 0.95, False),
    ("enum_accuracy", ">=", 0.92, False),
    ("boolean_f1", ">=", 0.95, False),
]
GATES_B = [
    ("body_gsm_exact", ">=", 0.55, False),
    ("body_gsm_within_1_step", ">=", 0.85, False),
    ("component_set_f1", ">=", 0.96, False),
]


def check_gates(metrics: dict, gates) -> tuple[list, bool]:
    rows, hard_ok = [], True
    for key, op, thr, hard in gates:
        v = metrics.get(key)
        if v is None:
            rows.append((key, op, thr, v, "SKIP", hard))
            continue
        ok = (v <= thr) if op == "<=" else (v >= thr)
        rows.append((key, op, thr, v, "PASS" if ok else "FAIL", hard))
        if hard and not ok:
            hard_ok = False
    return rows, hard_ok


# ── prediction sources ────────────────────────────────────────────────
def _load_gold(adapter: str, split: str) -> list[dict]:
    if split == "eval_real":
        p = eval_real_jsonl()
        if not p.exists() or p.stat().st_size == 0:
            print("[eval] eval_real is empty — see 03_DATASET/eval_real/"
                  "RECOVERY_NEEDED.md. Falling back to the held-out 'test' split.",
                  file=sys.stderr)
            return _read_jsonl(adapter_jsonl(adapter, "test"))
        return _read_jsonl(p)
    return _read_jsonl(adapter_jsonl(adapter, split))


def _predict(adapter: str, rows: list[dict], args) -> dict[str, dict]:
    if args.predictions:
        out = {}
        for r in _read_jsonl(Path(args.predictions)):
            out[r["id"]] = r
        return out
    # build chats and call a model
    from .data import to_messages
    from .config import load_config
    cfg = load_config(args.config, getattr(args, "overrides", None))
    chats, ids = [], []
    for r in rows:
        m = to_messages(r, adapter)["messages"][:2]      # system + user only
        chats.append(m)
        ids.append(r.get("id") or r.get("_id"))
    if args.server:
        from .serve import HttpClient
        cli = HttpClient(args.server)
        texts = [cli.complete(adapter, c[0]["content"], c[1]["content"]) for c in chats]
    else:
        from .serve import LocalEngine
        eng = LocalEngine(cfg)
        texts = eng.generate(adapter, chats)
    preds = {}
    for i, t in zip(ids, texts):
        try:
            preds[i] = {"id": i, "output": json.loads(t)}
        except json.JSONDecodeError:
            preds[i] = {"id": i, "output": {}}
    return preds


def run(args) -> int:
    rows = _load_gold(args.adapter, args.split)
    if args.limit:
        rows = rows[:args.limit]
    preds = _predict(args.adapter, rows, args)
    if args.adapter == "a":
        metrics = score_adapter_a(rows, preds)
        gate_rows, hard_ok = check_gates(metrics, GATES_A)
    else:
        metrics = score_adapter_b(rows, preds)
        gate_rows, hard_ok = check_gates(metrics, GATES_B)

    report = {"adapter": args.adapter, "split": args.split, "metrics": metrics,
              "gates": [{"metric": k, "op": op, "threshold": thr, "value": v,
                         "result": res, "hard": hard}
                        for (k, op, thr, v, res, hard) in gate_rows]}
    print(json.dumps(report, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n  GATE                       op   thr     value    result")
    for k, op, thr, v, res, hard in gate_rows:
        tag = " (hard)" if hard else ""
        print(f"  {k:26s} {op:2s} {thr:<6} {str(v):>8}   {res}{tag}")
    print(f"\n  {'ALL HARD GATES PASS' if hard_ok else 'HARD GATE FAILURE'}")
    return 0 if hard_ok else 2


def build_argparser(ap: argparse.ArgumentParser) -> argparse.ArgumentParser:
    ap.add_argument("--adapter", choices=["a", "b"], required=True)
    ap.add_argument("--split", default="test",
                    help="test | val | eval_real  (eval_real for adapter a)")
    ap.add_argument("--config", default=str(Path(__file__).parents[1] / "configs" /
                                            "adapter_a.yaml"))
    ap.add_argument("--server", help="URL of a running vLLM server")
    ap.add_argument("--predictions", help="pre-dumped {id,output} JSONL")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--out", help="write report JSON here")
    ap.add_argument("overrides", nargs="*",
                    help="config key=value overrides, e.g. serve.gpu_memory_utilization=0.75")
    return ap


if __name__ == "__main__":
    p = build_argparser(argparse.ArgumentParser("bomft.evaluate"))
    raise SystemExit(run(p.parse_args()))
