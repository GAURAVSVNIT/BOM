# Implementation notes — HPC training stack + pipeline fixes

**Date:** 2026-08-29
**Scope of this pass:** answer "is the code implemented to run on HPC H100?"
(it was not — the repo shipped reports + a CPU dataset pipeline only), build that
stack, and fix the issues raised in the repo analysis.

---

## 1 · New: `07_TRAINING/` — fine-tuning on the cluster

Implements plan §9 (fine-tuning) and §10 (evaluation). Nothing GPU-related
existed before; `IMPLEMENTATION_PLAN.md` only described it in prose. The
SLURM/env layer is built to the **Aurora HPC (SVNIT DoCSE/AI)** constraints the
user supplied: by-path conda env, `module load anaconda3-2024.2`, fractional GPU
via `--gres=shard:N`, `logs/%x_%j.{out,err}`, `runs/$RUN_NAME`, `data/` for
reports, and the `unset PYTHONPATH; export PYTHONNOUSERSITE=1` fix for the
anaconda module's leaked `nvidia-nccl-cu12` (`undefined symbol: ncclCommResume`).
The user's `setup_env.sh` (tmux/slow-PyPI/SLURM-guard notes, torch-first, retry
loop) is used verbatim as `hpc/setup_env.sh`, path-reconciled only.

Confirmed cluster layout:
- repo synced to `~/u24ai026/ANJANI_BOM_AGENT/`  (so `07_TRAINING/` == the training dir)
- conda env already built at `~/u24ai026/BOM/envs/ajani_bom_finetune`
- base model pre-staged at `~/u24ai026/BOM/model_weights`
- all four locations overridable via `BOM_CODE_DIR` / `BOM_ENV_DIR` / `BOM_BASE_MODEL` / `BOM_ANACONDA_MODULE`; single source is `hpc/_config.sh`.

| Piece | File(s) | What it does |
|---|---|---|
| Entry points | `finetune.py` · `evaluate.py` · `serve.py` | thin top-level wrappers matching the sample script's arg style (`--base-model`, `--adapter-dir`, `--report-out`, `--output-dir`). Wire base-model path + run dir through env; delegate to `bomft`. |
| HPC | `hpc/_config.sh` (paths + `activate_env` + `require_pkgs`) · `setup_env.sh` (user's, verbatim) · `prepare_data.sh` (no-op when repo synced whole) · `preflight.sh` · `submit_{finetune,evaluate,serve}.sh` | sbatch jobs source `_config.sh`; `shard:40` train / `shard:20` eval / `shard:60` serve; job names `ajani_bom_*`; `require_pkgs` fails early with a fix-it line if `unsloth`/`vllm` aren't in the env. |
| Config | `bomft/config.py` + `configs/*.yaml` | typed config, `${ENV}` expansion, `key=value` overrides, `train.output_dir` to pin `runs/$RUN_NAME`. Plan §9.2 hyperparams: A r16/α32/lr2e-4/2ep/seq2048, B r32/α64/lr1e-4/3ep/seq4096, **LoRA bf16 not QLoRA**. |
| Data | `bomft/data.py` | dataset JSONL → 3-message chat examples, compact-JSON targets, completion-only loss. Torch-free. |
| Schema | `bomft/schema.py` | `guided_json` schemas built **from the live `rules.py`** — grammar can't drift from the data. |
| Train | `bomft/train.py` | Two backends: **`hf`** (default) = `peft.LoraConfig` + `AutoModelForCausalLM` + `trl.SFTTrainer` on a `messages` dataset with `assistant_only_loss` — matches the Aurora env (torch 2.13 / transformers 5 / peft 0.20 / trl 1.9); **`unsloth`** = the `FastLanguageModel` path, opt-in. `SFTConfig` kwargs are filtered against `dataclasses.fields()` so trl point-release drift can't crash it. bf16, early-stop on eval loss; writes `runs/$RUN_NAME/{adapter/,config.resolved.json,train_result.json}`. |
| Serve | `bomft/serve.py` | vLLM OpenAI server, **both LoRA adapters hot**, xgrammar guided decoding; plus in-process `LocalEngine` and stdlib `HttpClient`. Adapter dirs via `$BOM_ADAPTER_{A,B}_DIR`. |
| Eval | `bomft/evaluate.py` | plan §10.2 gates. Adapter-A **hallucination rate < 2%** (operational form: gold `not_specified` but model asserts a value) + a strict `evidence_violation_rate` where the model supplies spans; numeric/enum/bool. Adapter-B GSM-exact / within-one-step / component-F1 / family acc. Non-zero exit on hard-gate fail. Torch-free metric core. |
| Preflight | `bomft/preflight.py` | model-path + dataset + config + schema checks (login node) and GPU/sm_90 + bf16 + VRAM checks (compute node). |
| Tests | `tests/` | **12 torch-free tests** — data format, the issue-#1 invariant on the real dataset, schema enum-pinning, every metric function incl. a perfect-prediction zero-hallucination check. |

```bash
# login node, in tmux (PyPI ~40 kB/s, torch ~2 GB)
cd ~/u24ai026/ANJANI_BOM_AGENT/07_TRAINING
bash hpc/setup_env.sh                    # env at ~/u24ai026/BOM/envs/ajani_bom_finetune (tops up if it exists)
bash hpc/preflight.sh
sbatch hpc/submit_finetune.sh a   ;  sbatch hpc/submit_finetune.sh b
sbatch hpc/submit_evaluate.sh a   ;  sbatch hpc/submit_evaluate.sh b
sbatch hpc/submit_serve.sh
```

---

## 2 · New: `bom_agent/` — inference pipeline scaffold (plan §2/§3)

End-to-end wiring, runs **with no GPU** (deterministic fallbacks) or against the
vLLM server (`--server URL`):

```
ingest → extract (adapter A) → classify/derive → retrieve top-3
       → envelope → configure (adapter B) → render → solve → validate → dual output
```

`python -m bom_agent.cli run --text "U PANNEL BAG 85X85X85 …"` prints a BOM that
leads with construction type, then weight + GSM (plan H5), then the clarification
list. The model line is crossed only in `extract()` and `configure()`; both take
an optional client and fall back to deterministic logic. 4 tests, all pass.

Not fully built (matches "scaffold"): the deterministic renderer is the minimal
one the dataset ships with (plan Phase 2 is the full one); the rule *registry*
is still Python (`rules_registry.py` is the seam for the future JSON registry).

---

## 3 · Fixes to the data pipeline (`03_DATASET/build/`)

| # | Issue | Fix | Verified |
|---|---|---|---|
| **#2** | Every stage hard-coded `ROOT = r"C:\Users\Nikhil1616\Desktop\BOM"`; not runnable from the collected folder. | New `build/_bompaths.py`: `$BOM_ROOT` / `$BOM_DATASET_DIR` with checkout defaults; all 11 stages patched. Both historical layouts still work with zero config. | 04–10 run clean from this folder. |
| **#1** | `06_adapter_a.py` marked internal dims / `static_type` `state=provided` in **~67 %** of adapter-A training targets with no support in the enquiry text — training the hallucination the firewall exists to prevent. | Internal dims are all-or-nothing and style-gated; `static_type`/`product_contents` never "visible"; round-trip `verify_parse`/`CHECK` extended to the internal triple. | **1093 → 0** unsupported labels; 399 legit internal triples kept. Regression test in `07_TRAINING/tests/test_data.py`. |
| **#4** | `05_split.py` sent every family with < 4 fingerprint groups entirely to `train` (platten/container_liner/tunnel/hood had zero held-out coverage). | Families with 2–3 groups now contribute one held-out group (alternating val/test); genuine singletons stay train-only and are **reported** in a "DEGRADED EVAL COVERAGE" table. Zero-leakage preserved. | `tunnel` now in `test`; leakage gate still PASS. |
| **#5** | `classify_family` matched bare `TYPE C` → a Type-C *static class* bag misclassified as `two_panel`. | Dropped the reversed `TYPE\s*-?\s*C` alternative; kept `C-TYPE` / `C TYPE`. | — |
| **#9** (new, self-inflicted) | Re-running `09_eval_real.py` here — where `All_Things/` is absent by design — **truncated `eval_real/eval_real.jsonl` (13 rows) and `pending_ocr.json` (8 entries) to empty.** No copy exists on this machine; not recoverable byte-exact. | `09_eval_real.py` now refuses to overwrite when it finds no source PDFs (`BOM_EVAL_FORCE=1` to override). Everything else regenerated **byte-identical** (checked vs original `MANIFEST.json` hashes). | See `03_DATASET/eval_real/RECOVERY_NEEDED.md` — one command restores the 13+8 from a tree that has `All_Things/`. |

Also observed, not changed (larger scope, already tracked in the plan):

* **#3** renderer incompleteness (median replay error 10.16 %; 5 families with no
  geometry) — plan Phase 2. The `bom_agent` solver surfaces it as a V18 warning +
  clarification rather than forcing, which is the designed behaviour.
* **#7** the family list differs across `IMPLEMENTATION_PLAN §1.2` / `§13.5` /
  `rules.py`. `rules.FAMILIES` (16 incl. notebook additions) is treated as the
  single source; `bom_agent` and `bomft.schema` both read from it.
* `gold/physical_bom.jsonl` re-generated with a different hash than shipped — the
  shipped copy was already stale vs `rules.py`; it is "renderer tests only",
  never a training target. Now in sync.
