# Anjani FIBC BOM — Fine-tuning Dataset v1.0.0

**Built:** 2026-08-29  ·  **Rule book version:** 1.1
**Location:** `dataset/`  ·  **Builders:** `dataset/build/00_…10_*.py` (deterministic, re-runnable)

---

## 1 · What was read

| | |
|---|---|
| Workbooks found across the whole project | **130** |
| Unique by content hash (duplicates dropped per H1) | **119** |
| Sheets read | **744** |
| **BOM sheets parsed** | **482** |

The earlier naive extractor found 395 BOM sheets in `All_Things` alone.
Sweeping every folder and reading merge-aware found **482** — a **+22%** recovery.

## 2 · Extraction accuracy

Engine choice was decided from an empirical diagnostic (`diagnostic.json`), not from defaults:

- **33,757 formula cells, 0 uncached** → `openpyxl(data_only=True)` is safe on this corpus; no LibreOffice recalculation pass needed.
- **174,841 cells sit inside merged ranges** across 116 of 119 workbooks. `openpyxl` returns `None` for every one. Every read is merge-aware and every cell records whether its value is its **own** or an **echo** of a merge origin.
- **55 workbooks carry drawings**; text is pulled straight from the OOXML zip (only 1 carried actual text — the rest are diagrams, so nothing was lost).
- Every value is read **twice**, by `openpyxl` and by `python-calamine`, and reconciled.

| | |
|---|---|
| Cells compared across both engines | **172,092** |
| **Two-engine agreement** | **99.8454%** |
| Remaining disagreements | 234 — all Excel error cells (`#DIV/0!`, `#NAME?`) |
| **Cells recovered by merge-awareness** | **109,160** |

One file, `All_Things/FIBC PRODUCTION DEC-2025.xlsx`, is **0 bytes** — empty, not corrupt. That closes open item H6.

## 3 · The four gold layers

| Layer | Rows | What it is |
|---|---:|---|
| `gold/order_spec.jsonl` | 482 | what the customer asked — **header block only** |
| `gold/build_spec.jsonl` | 482 | what the engineer decided |
| `gold/physical_bom.jsonl` | 482 | what was actually cut — renderer tests only |
| `gold/clarification.jsonl` | 482 | what the agent should ask |

**Firewall: PASS.** `build_order_spec()` is never handed the component table, and a test asserts no BuildSpec-only field appears in any OrderSpec or any adapter-A target.

Family distribution: u_panel 211, circular 114, four_panel_baffle 71, two_panel 35, single_loop 14, two_loop 11, four_panel 11, omega 6

## 4 · Adapter A — extraction

`enquiry text → OrderSpec`

| | |
|---|---:|
| Candidates generated | 1,635 |
| **Kept after round-trip verification** | **1,621 (99.1%)** |
| Discarded | 14 |
| train / val / test | **1129 / 265 / 235** |
| Hand-written hard negatives | 8 |

Five styles, evenly balanced: `whatsapp_en`, `whatsapp_hinglish`, `email_formal`, `tds_table`, `phone_notes`.

**Round-trip verification.** Text is synthesised from `OrderSpec_gold`; an *independent* parser — sharing no code with the generator — re-reads the generated text and must recover the same values. Any mismatch is **discarded, never repaired**. Field dropout follows the corpus rates (liner absent 78%, printing 43%, target weight 9%, SWL 5%), and corpus noise is injected (`PANNEL`, `CLOUSER`, `gr/m2`, `3"`, `05:01`, `6:01/UN`).

Each style is graded only on fields it can structurally express — a printed TDS carries no LL/SL loop lengths, so grading it on those would discard sound rows.

## 5 · Adapter B — configuration

`OrderSpec + retrieved top-3 + rule envelope → BuildSpec`

| Row type | Count | Source |
|---|---:|---|
| `base` | 354 | **real engineering decisions, zero labelling** |
| `solver_feedback` | 382 | a knob perturbed, weight gap shown, model must move it back |
| `conflict` | 61 | customer GSM below the chart floor — honour it and flag |
| `conflict_infeasible` | 97 | target weight unreachable — must ask, never force |
| **train / val / test** | **787 / 56 / 51** | |

Retrieval is **leave-one-fingerprint-out** with a hard family filter, so a sheet can never see its own twin.

Solver rows perturb knobs **in the engineer's order** — belt GPM, then loop cut, then body GSM — and the target is anchored on the renderer's own baseline for the true BuildSpec, so the gap isolates the perturbation rather than measuring renderer incompleteness.

## 6 · eval_real — never trained on

**0 real customer documents** with a text layer: 6 `SPEC JIEXP` technical data sheets and 7 `COMPONENT` spec sheets. Imperial units, `gr/m2`, `Dia`, Spanish `REVISIÓN`, and typos (`lenght`, `wehite`). Pre-filled by rule, **awaiting one pass of human confirmation**.

**0 scanned enquiries have no text layer** and are listed in `eval_real/pending_ocr.json` for OCR plus hand labelling — flagged honestly rather than silently dropped.

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
| Sheets rendered | 455 |
| **Median grand-total error** | **10.162%** |
| Within 5% | 29.2% |
| Within 10% | 49.7% |

Component geometry within 2 cm:

| Component | Agreement |
|---|---:|
| SIDE PANEL cut | 96.9% |
| DISCHARGE SPOUT cut | 94.5% |
| FILLING SPOUT cut | 91.7% |
| FILLING SPOUT width | 85.2% |
| SIDE PANEL width | 84.5% |
| BODY PANEL width | 76.5% |
| BODY PANEL cut | 73.9% |
| CORNER LOOP cut | 57.2% |

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
