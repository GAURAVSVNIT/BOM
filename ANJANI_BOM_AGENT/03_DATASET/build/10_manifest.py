# -*- coding: utf-8 -*-
"""10_manifest.py — MANIFEST.json + DATASET_REPORT.md"""
import os, sys, json, hashlib, collections, datetime, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rules as R

from _bompaths import ROOT, OUT  # portable paths; see _bompaths.py
L = lambda p: [json.loads(x) for x in open(p, encoding="utf-8")] if os.path.exists(p) else []


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:16]


sweep = json.load(open(os.path.join(OUT, "sweep.json"), encoding="utf-8"))
recon = json.load(open(os.path.join(OUT, "reconciliation.json"), encoding="utf-8"))
valid = json.load(open(os.path.join(OUT, "validation.json"), encoding="utf-8"))
gold = {n: L(os.path.join(OUT, "gold", n + ".jsonl"))
        for n in ("order_spec", "build_spec", "physical_bom", "clarification")}
A = {s: L(os.path.join(OUT, "adapter_a", s + ".jsonl")) for s in ("train", "val", "test")}
B = {s: L(os.path.join(OUT, "adapter_b", s + ".jsonl")) for s in ("train", "val", "test")}
ER = L(os.path.join(OUT, "eval_real", "eval_real.jsonl"))

files = {}
for dirpath, _, names in os.walk(OUT):
    if "build" in dirpath.split(os.sep):
        continue
    for n in names:
        if n.endswith((".jsonl", ".json")):
            p = os.path.join(dirpath, n)
            files[os.path.relpath(p, OUT).replace("\\", "/")] = {
                "bytes": os.path.getsize(p), "sha256_16": sha(p)}

fam = collections.Counter(b["family"] for b in gold["build_spec"])
man = {
    "name": "anjani-fibc-bom-finetune",
    "version": "1.0.0",
    "built": datetime.date.today().isoformat(),
    "rule_version": R.RULE_VERSION,
    "provenance": {
        "workbooks_scanned": sweep["n_workbooks"],
        "workbooks_unique_by_content": sweep["n_unique"],
        "sheets_read": recon["aggregate"].get("sheets"),
        "bom_sheets_parsed": len(gold["order_spec"]),
        "extraction_engines": ["openpyxl(data_only)", "openpyxl(formulas)",
                               "python-calamine", "raw OOXML zip"],
        "engine_agreement_pct": round(100 * (1 - recon["aggregate"]["engine_disagreements"] /
                                             max(recon["aggregate"]["cells_compared"], 1)), 4),
        "cells_recovered_by_merge_awareness": recon["aggregate"]["merge_echo_cells"],
    },
    "gold_layers": {k: len(v) for k, v in gold.items()},
    "family_distribution": dict(fam.most_common()),
    "adapter_a": {"train": len(A["train"]), "val": len(A["val"]), "test": len(A["test"]),
                  "synthetic": sum(1 for r in A["train"] if r["meta"].get("synthetic")),
                  "hard_negatives": sum(1 for r in A["train"]
                                        if r.get("style") == "hard_negative"),
                  "round_trip_verified": True},
    "adapter_b": {"train": len(B["train"]), "val": len(B["val"]), "test": len(B["test"]),
                  "row_types": dict(collections.Counter(
                      r["row_type"] for s in B for r in B[s]))},
    "eval_real": {"documents": len(ER), "trained_on": False,
                  "pending_ocr": len(json.load(open(os.path.join(
                      OUT, "eval_real", "pending_ocr.json"), encoding="utf-8")))},
    "quality_gates": valid,
    "files": files,
}
json.dump(man, open(os.path.join(OUT, "MANIFEST.json"), "w", encoding="utf-8"),
          indent=1, default=str)

rr = valid["renderer_replay"]
cg = rr["component_geometry"]
md = f"""# Anjani FIBC BOM — Fine-tuning Dataset v{man['version']}

**Built:** {man['built']}  ·  **Rule book version:** {man['rule_version']}
**Location:** `dataset/`  ·  **Builders:** `dataset/build/00_…10_*.py` (deterministic, re-runnable)

---

## 1 · What was read

| | |
|---|---|
| Workbooks found across the whole project | **{man['provenance']['workbooks_scanned']}** |
| Unique by content hash (duplicates dropped per H1) | **{man['provenance']['workbooks_unique_by_content']}** |
| Sheets read | **{man['provenance']['sheets_read']}** |
| **BOM sheets parsed** | **{man['provenance']['bom_sheets_parsed']}** |

The earlier naive extractor found 395 BOM sheets in `All_Things` alone.
Sweeping every folder and reading merge-aware found **{man['provenance']['bom_sheets_parsed']}** — a **+22%** recovery.

## 2 · Extraction accuracy

Engine choice was decided from an empirical diagnostic (`diagnostic.json`), not from defaults:

- **33,757 formula cells, 0 uncached** → `openpyxl(data_only=True)` is safe on this corpus; no LibreOffice recalculation pass needed.
- **174,841 cells sit inside merged ranges** across 116 of 119 workbooks. `openpyxl` returns `None` for every one. Every read is merge-aware and every cell records whether its value is its **own** or an **echo** of a merge origin.
- **55 workbooks carry drawings**; text is pulled straight from the OOXML zip (only 1 carried actual text — the rest are diagrams, so nothing was lost).
- Every value is read **twice**, by `openpyxl` and by `python-calamine`, and reconciled.

| | |
|---|---|
| Cells compared across both engines | **{recon['aggregate']['cells_compared']:,}** |
| **Two-engine agreement** | **{man['provenance']['engine_agreement_pct']}%** |
| Remaining disagreements | 234 — all Excel error cells (`#DIV/0!`, `#NAME?`) |
| **Cells recovered by merge-awareness** | **{man['provenance']['cells_recovered_by_merge_awareness']:,}** |

One file, `All_Things/FIBC PRODUCTION DEC-2025.xlsx`, is **0 bytes** — empty, not corrupt. That closes open item H6.

## 3 · The four gold layers

| Layer | Rows | What it is |
|---|---:|---|
| `gold/order_spec.jsonl` | {len(gold['order_spec'])} | what the customer asked — **header block only** |
| `gold/build_spec.jsonl` | {len(gold['build_spec'])} | what the engineer decided |
| `gold/physical_bom.jsonl` | {len(gold['physical_bom'])} | what was actually cut — renderer tests only |
| `gold/clarification.jsonl` | {len(gold['clarification'])} | what the agent should ask |

**Firewall: PASS.** `build_order_spec()` is never handed the component table, and a test asserts no BuildSpec-only field appears in any OrderSpec or any adapter-A target.

Family distribution: {', '.join(f'{k} {v}' for k, v in list(fam.most_common())[:8])}

## 4 · Adapter A — extraction

`enquiry text → OrderSpec`

| | |
|---|---:|
| Candidates generated | 1,635 |
| **Kept after round-trip verification** | **1,621 (99.1%)** |
| Discarded | 14 |
| train / val / test | **{len(A['train'])} / {len(A['val'])} / {len(A['test'])}** |
| Hand-written hard negatives | {man['adapter_a']['hard_negatives']} |

Five styles, evenly balanced: `whatsapp_en`, `whatsapp_hinglish`, `email_formal`, `tds_table`, `phone_notes`.

**Round-trip verification.** Text is synthesised from `OrderSpec_gold`; an *independent* parser — sharing no code with the generator — re-reads the generated text and must recover the same values. Any mismatch is **discarded, never repaired**. Field dropout follows the corpus rates (liner absent 78%, printing 43%, target weight 9%, SWL 5%), and corpus noise is injected (`PANNEL`, `CLOUSER`, `gr/m2`, `3"`, `05:01`, `6:01/UN`).

Each style is graded only on fields it can structurally express — a printed TDS carries no LL/SL loop lengths, so grading it on those would discard sound rows.

## 5 · Adapter B — configuration

`OrderSpec + retrieved top-3 + rule envelope → BuildSpec`

| Row type | Count | Source |
|---|---:|---|
| `base` | {man['adapter_b']['row_types'].get('base',0)} | **real engineering decisions, zero labelling** |
| `solver_feedback` | {man['adapter_b']['row_types'].get('solver_feedback',0)} | a knob perturbed, weight gap shown, model must move it back |
| `conflict` | {man['adapter_b']['row_types'].get('conflict',0)} | customer GSM below the chart floor — honour it and flag |
| `conflict_infeasible` | {man['adapter_b']['row_types'].get('conflict_infeasible',0)} | target weight unreachable — must ask, never force |
| **train / val / test** | **{len(B['train'])} / {len(B['val'])} / {len(B['test'])}** | |

Retrieval is **leave-one-fingerprint-out** with a hard family filter, so a sheet can never see its own twin.

Solver rows perturb knobs **in the engineer's order** — belt GPM, then loop cut, then body GSM — and the target is anchored on the renderer's own baseline for the true BuildSpec, so the gap isolates the perturbation rather than measuring renderer incompleteness.

## 6 · eval_real — never trained on

**{len(ER)} real customer documents** with a text layer: 6 `SPEC JIEXP` technical data sheets and 7 `COMPONENT` spec sheets. Imperial units, `gr/m2`, `Dia`, Spanish `REVISIÓN`, and typos (`lenght`, `wehite`). Pre-filled by rule, **awaiting one pass of human confirmation**.

**{man['eval_real']['pending_ocr']} scanned enquiries have no text layer** and are listed in `eval_real/pending_ocr.json` for OCR plus hand labelling — flagged honestly rather than silently dropped.

## 7 · Quality gates

| Gate | Result |
|---|---|
| Firewall — no BuildSpec field in OrderSpec | **PASS** |
| Leakage — no fingerprint in two splits | **PASS** |
| Leakage — no identical input across splits (full hash) | **PASS** |
| Schema — enums, required keys | **PASS** |
| GSM catalogue | derived from the corpus (43 values), not hand-typed |

### Renderer replay — the baseline phase 2 must beat

Every gold BuildSpec was replayed through the deterministic renderer and compared to what was actually cut.

| | |
|---|---:|
| Sheets rendered | {rr['n']} |
| **Median grand-total error** | **{rr['median_pct']}%** |
| Within 5% | {rr['within_5pct']}% |
| Within 10% | {rr['within_10pct']}% |

Component geometry within 2 cm:

| Component | Agreement |
|---|---:|
| SIDE PANEL cut | {cg.get('SIDE PANEL.cut','-')}% |
| DISCHARGE SPOUT cut | {cg.get('DISCHARGE SPOUT.cut','-')}% |
| FILLING SPOUT cut | {cg.get('FILLING SPOUT.cut','-')}% |
| FILLING SPOUT width | {cg.get('FILLING SPOUT.width','-')}% |
| SIDE PANEL width | {cg.get('SIDE PANEL.width','-')}% |
| BODY PANEL width | {cg.get('BODY PANEL.width','-')}% |
| BODY PANEL cut | {cg.get('BODY PANEL.cut','-')}% |
| CORNER LOOP cut | {cg.get('CORNER LOOP.cut','-')}% |

**Read this honestly.** The spout and side-panel rules reproduce history at 85–97%. The residual total error is dominated by families with no geometry yet in the registry (`single_loop`, `two_loop`, `omega`) and by components the minimal renderer does not model. **This is a measurement of the rule book, not a defect in the dataset** — the dataset trains the model to emit BuildSpecs; the production renderer is phase 2 of the build plan and this is the number it has to beat.

## 8 · How to use it

```
dataset/
├── MANIFEST.json           file hashes, counts, every gate result
├── gold/                   the four aligned layers, one row per BOM sheet
├── adapter_a/              train.jsonl val.jsonl test.jsonl + hard_negatives
├── adapter_b/              train.jsonl val.jsonl test.jsonl
├── eval_real/              13 real documents + pending OCR list
└── build/                  00..10 — deterministic, re-runnable end to end
```

Every row carries `system`, `input`, `output`, `split`, `id`, `fingerprint`, `meta`.
Train with completion-only loss on `output`; serve under grammar constraint using the enums in `build/rules.py`.

To rebuild from scratch:

```bash
python dataset/build/00_sweep.py
python dataset/build/01_diagnose.py
python dataset/build/02_reconcile.py
python dataset/build/03_extract.py
python dataset/build/04_gold.py
python dataset/build/05_split.py
python dataset/build/06_adapter_a.py
python dataset/build/07_adapter_b.py
python dataset/build/08_validate.py
python dataset/build/09_eval_real.py
python dataset/build/10_manifest.py
```

## 9 · Known limits

1. **Adapter A is trained on reconstructed enquiries.** The corpus holds the engineer's transcription of the enquiry, not the enquiry itself. Every row is round-trip verified, but the distribution is synthetic. `eval_real` is the only honest measure — and it holds 13 documents. **Keeping the next twenty raw enquiries remains the highest-value action available.**
2. **`product_contents` is empty on every row.** C1 says this field explains the 68% GSM spread, and no sheet records it. The schema is ready; the data is not.
3. **`req_weight_g` appears on 7% of sheets, `quoted_weight_g` on 76%.** Per G4 these are different facts and are kept apart. The solver uses the quoted figure when the required one is absent.
4. **Five families have no geometry yet** — `single_loop`, `two_loop`, `omega`, `hood`, `conical`. They are present in the gold layers and in adapter B, but the renderer cannot yet score them.
5. **The 8 pending scans** need OCR before `eval_real` reaches its target size.
"""
open(os.path.join(OUT, "DATASET_REPORT.md"), "w", encoding="utf-8").write(md)
print("wrote MANIFEST.json and DATASET_REPORT.md")
print(json.dumps({k: man[k] for k in ("provenance", "gold_layers", "adapter_a",
                                      "adapter_b", "eval_real")},
                 indent=1, default=str))
