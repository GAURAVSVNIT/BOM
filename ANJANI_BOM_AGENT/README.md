# Anjani FIBC BOM Agent — complete working folder

**Assembled:** 26 August 2026
**Contents:** everything produced for the new BOM generation architecture — the analysis, the questions put to the engineer, his answers, the locked rule book, the implementation plan, and the finished fine-tuning dataset.

> These are **copies**. Every original is still in its place under `Desktop\BOM\`. Nothing was moved or deleted, so the dataset build scripts continue to work against their existing paths.

---

## Start here

| If you want to… | Open |
|---|---|
| **Understand the whole system and build it** | `01_REPORTS/IMPLEMENTATION_PLAN.md` — the main document, v1.1 |
| See the finished training data and how good it is | `01_REPORTS/DATASET_REPORT.md` |
| Read the rules the engineer confirmed or corrected | `01_REPORTS/FINAL_SYSTEM_REPORT.md` |
| Review the questions and his answers side by side | `01_REPORTS/ENGINEER_QUESTIONNAIRE.md` then `05_ENGINEER_INPUT/ANSWERS_to_44_questions.md` |
| Browse the same reports as web pages | `02_WEB_REPORTS/ARTIFACT_LINKS.md` |
| Train a model today | `03_DATASET/adapter_a/` and `03_DATASET/adapter_b/` |
| **Fine-tune on the cluster (SLURM · 1×H100)** | `07_TRAINING/README.md` — Unsloth LoRA + vLLM serving + eval gates |
| Run the end-to-end pipeline (no GPU needed) | `python -m bom_agent.cli run --text "…"` — see `bom_agent/` |
| What was added/fixed on 2026-08-29 | `IMPLEMENTATION_NOTES.md` |

---

## 01_REPORTS — the four written deliverables

| File | What it is |
|---|---|
| `IMPLEMENTATION_PLAN.md` | **The main document.** v1.1, build-ready. The locked rule book (§1), the nine-stage architecture (§2), repository layout (§3), the four data contracts (§4), renderer (§5), solver (§6), 21 validators (§7), data pipeline (§8), fine-tuning config (§9), acceptance gates (§10), a nine-phase schedule (§11), open items (§12), and everything derived from the engineer's notebook (§13). |
| `FINAL_SYSTEM_REPORT.md` | What his 44 answers changed — eleven design decisions, four rules that failed against the data, and the corrected rule book. |
| `ENGINEER_QUESTIONNAIRE.md` | The rules derived from 395 sheets, plus the 44 questions, each carrying the measurement that prompted it. This is the document he wrote his answers onto. |
| `DATASET_REPORT.md` | How the dataset was extracted, built and verified. Every number reproducible. |

## 02_WEB_REPORTS — the same reports as browsable pages

Six standalone HTML files, openable offline in any browser, plus `ARTIFACT_LINKS.md` with the live links to the private Artifacts on claude.ai.

## 03_DATASET — the fine-tuning dataset, v1.0

```
03_DATASET/
├── MANIFEST.json        file hashes, counts, every quality-gate result
├── DATASET_REPORT.md
├── gold/                4 × 482 rows, aligned by _id and _fingerprint
│     order_spec.jsonl        what the customer asked   (header block only)
│     build_spec.jsonl        what the engineer decided
│     physical_bom.jsonl      what was actually cut     (renderer tests only)
│     clarification.jsonl     what the agent should ask
├── adapter_a/           extraction · train 1113 · val 270 · test 246
│                        + hard_negatives.jsonl (8, hand written)
├── adapter_b/           configuration · train 803 · val 57 · test 55
├── eval_real/           13 real customer documents — NEVER train on these
│                        + pending_ocr.json (8 scans awaiting OCR)
└── build/               00…10 + 99_collect — deterministic, re-runnable
      xl_read.py         the multi-engine, merge-aware spreadsheet reader
      bom_parse.py       the BOM sheet parser
      rules.py           the locked rule book, as data
      renderer.py        BuildSpec → weight
```

Rebuild the whole thing from scratch:

```bash
cd C:\Users\Nikhil1616\Desktop\BOM
python dataset/build/00_sweep.py        # find + dedupe every workbook
python dataset/build/01_diagnose.py     # measure what each engine would miss
python dataset/build/02_reconcile.py    # two-engine cross-check
python dataset/build/03_extract.py      # parse every BOM sheet
python dataset/build/04_gold.py         # the four gold layers + firewall test
python dataset/build/05_split.py        # dedupe + fingerprint split
python dataset/build/06_adapter_a.py    # extraction rows, round-trip verified
python dataset/build/07_adapter_b.py    # configuration + solver + conflict rows
python dataset/build/08_validate.py     # four quality gates
python dataset/build/09_eval_real.py    # the real-document eval set
python dataset/build/10_manifest.py     # manifest + report
```

Dependencies: `openpyxl`, `python-calamine`, `PyMuPDF` (`fitz`).

## 04_ANALYSIS — the working behind every number quoted

`scripts/` holds the fifteen analysis scripts used across the project — the corpus scans, the GSM predictor tests, the rule-verification passes against the engineer's answers and his notebook, and the PDF readers. `outputs/` holds `corpus_allthings.json` (the 395-sheet extraction the questionnaire was written from) and the raw rule-analysis output.

These are the scripts that produced the claims: the 68% GSM spread, the target-weight inversion result, the 87.2% loop-formula agreement, the 93% baffle-Pythagoras match, and the belt-strength check that turned V09 from a rejection into a warning.

## 05_ENGINEER_INPUT — what the engineer gave back

| Item | What it is |
|---|---|
| `ANSWERS_to_44_questions.md` | His answers written into the questionnaire. The source for every `[E, …]` citation in the rule book. |
| `Rules from Data.pdf` | 22 pages of the derived rules with his handwritten corrections — the source of the nine rule changes and five new tables. |
| `rules_pdf_pages_readable/` | The same 22 pages rendered as legible JPGs (the PDF has no text layer). |

## 06_REFERENCE — the source material the rules were checked against

| Item | Why it matters |
|---|---|
| `REFERENCE_BOM_85x85x85 (filename says 90x90x90).xlsx` | The reference BOM. Its contents are 85×85×85 while the filename says 90×90×90 — which is why filenames are never used to label training data. |
| `GSM- GPM VS SWL-SF.xlsx` | The company's own GSM and belt charts, transcribed into `rules.py`. |
| `fibc_domain_notes/` | The eight domain reference files on construction, types A–D, liners, manufacturing. |
| Three National Bulk Bag PDFs | Bulk density list (needed for deriving SWL from product + volume), UN certification, buyer's guide. |

---

## What is deliberately **not** in here

`All_Things/` — your 107 production workbooks. That is your source data, not something this project produced, and it stays in `Desktop\BOM\All_Things\`. The dataset build scripts read it from there. Everything derived from it *is* in `03_DATASET/`.

---

## The state of things, in one paragraph

The architecture is settled: a fine-tuned Qwen adapter reads the enquiry and emits only what the customer said; a second adapter makes roughly seventy closed-vocabulary engineering decisions informed by the three nearest bags and the chart bands; deterministic code turns those decisions into every number on the sheet; a solver adjusts loop gramage, then loop cut, then body GSM until the bag lands within ±2% of the PO weight less one percent; and where the enquiry contradicts itself the agent builds both options and hands the engineer the question to put to the customer. The rule book is locked at v1.1 against 44 answers, 22 pages of handwritten corrections and sixty pages of the engineer's notebook. The dataset is built and verified: 482 BOM sheets read at 99.85% two-engine agreement, four gold layers, 1,629 extraction rows at 99.1% round-trip verification, 915 configuration rows of which 354 are real engineering decisions, and all four quality gates passing. Five open items remain, none blocking. The highest-value action still available is the simplest: **keep the next twenty raw customer enquiries exactly as they arrive.**
