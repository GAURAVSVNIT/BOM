# `eval_real/` needs regeneration

## What happened

During the HPC/fixes work (2026-08-29), `09_eval_real.py` was run inside this
collected `ANJANI_BOM_AGENT/` folder. That folder **deliberately ships without
`All_Things/`** (see the top-level `README.md`), so the stage found zero source
PDFs and, as originally written, truncated its outputs:

| File | Was | Became |
|---|---|---|
| `eval_real/eval_real.jsonl` | 13 rows / 21,049 bytes (`sha256_16 2d2c35d76d597f7d`) | empty |
| `eval_real/pending_ocr.json` | 8 entries / 1,271 bytes (`sha256_16 ae6ee672dc2f4067`) | `[]` |

No copy of the original content exists on this machine and the folder is not
under version control, so byte-exact restore is not possible here. Everything
else in `03_DATASET/` was regenerated **byte-identical** (verified against the
original `MANIFEST.json` hashes) — only these two files were lost, and neither
is a training input (`eval_real` is held-out; `train_on_this: false` on every row).

## Fix applied

`09_eval_real.py` now **refuses to overwrite** existing outputs when it finds no
source documents (set `BOM_EVAL_FORCE=1` to override). This cannot recur.

## How to fully restore (≈30 seconds, on a machine that has `All_Things/`)

```bash
# point BOM_ROOT at the tree that contains All_Things/  (the old Desktop\BOM)
BOM_ROOT="/path/to/Desktop/BOM" python 03_DATASET/build/09_eval_real.py
BOM_ROOT="/path/to/Desktop/BOM" python 03_DATASET/build/10_manifest.py
```

The original set: **13 text-layer documents** (6 `SPEC JIEXP-0xx.pdf` +
7 `COMPONENT C2x SPEC.PDF`) written to `eval_real.jsonl`, and **8 scanned
enquiries** with no text layer listed in `pending_ocr.json` for OCR + hand
labelling. Regeneration is deterministic and will reproduce them exactly.
