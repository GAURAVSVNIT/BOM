# 07_TRAINING — Anjani BOM agent fine-tuning (Aurora HPC · SVNIT DoCSE/AI)

Implements plan §9 (fine-tuning) and §10 (evaluation): two LoRA adapters on one
pre-staged Qwen base (4B or 8–9B), trained with **peft + trl** (`backend=hf`,
matches the Aurora env: torch 2.13 / transformers 5 / trl 1.9 — Unsloth is an
opt-in `backend=unsloth`), served with **vLLM** under grammar-constrained JSON
decoding, evaluated against the plan's ship gates.

Built for the Aurora cluster's constraints: no `pip`/`curl` on the base PATH,
no sudo, compute nodes have no internet route, ~40 kB/s login-node PyPI, the
`anaconda3-2024.2` module leaks an old `nvidia-nccl-cu12`. All handled.

**Training needs only** `torch transformers peft trl datasets accelerate` (all
already in the env). `vllm` is needed for eval/serve only; `unsloth` only for
`backend=unsloth`.

```
07_TRAINING/   ==   ~/u24ai026/ANJANI_BOM_AGENT/07_TRAINING/   on the cluster
├── finetune.py  evaluate.py  serve.py     top-level entry points
├── bomft/                                 package: config·data·schema·train·serve·evaluate
├── configs/     adapter_a.yaml  adapter_b.yaml  serve.yaml
├── hpc/         _config.sh  setup_env.sh  prepare_data.sh  preflight.sh
│                submit_{finetune,evaluate,serve}.sh
├── tests/       torch-free unit tests
├── requirements.txt   pyproject.toml   environment.yml
├── data/        (created) eval reports
└── runs/        (created) runs/qwen_bom_lora_{a,b}_v1/{adapter/,config.resolved.json,...}
```

## Paths — one place: `hpc/_config.sh`

| var | default | override |
|---|---|---|
| `CODE_DIR` | `~/u24ai026/ANJANI_BOM_AGENT` | `BOM_CODE_DIR` |
| `ENV_DIR` | `~/u24ai026/BOM/envs/ajani_bom_finetune` | `BOM_ENV_DIR` |
| `BASE_MODEL` | `~/u24ai026/BOM/model_weights` | `BOM_BASE_MODEL` |
| `ANACONDA_MODULE` | `anaconda3-2024.2` | `BOM_ANACONDA_MODULE` (try `anaconda3_new`) |

Every `hpc/submit_*.sh` sources `_config.sh`, then `activate_env` does:
`module load`, `conda activate "$ENV_DIR"`, **`unset PYTHONPATH`**,
**`export PYTHONNOUSERSITE=1`** (the nccl fix), offline env vars, `cd 07_TRAINING`,
`mkdir -p logs data`. `require_pkgs` fails the job early with a fix-it message if
a needed package is missing from the env.

## Run it

```bash
cd ~/u24ai026/ANJANI_BOM_AGENT/07_TRAINING

# --- LOGIN NODE ---
bash hpc/preflight.sh                    # confirms the [req] training packages are present
# if [req] all present -> straight to training. Optional cleanup of the two cosmetic gaps:
#   pip install kernels pytest           (silences a transformers warning; enables `pytest`)

# --- SUBMIT (fractional GPU via --gres=shard:N) ---
sbatch hpc/submit_finetune.sh a data.max_examples=64 train.epochs=1 train.eval_steps=10   # smoke, ~2 min
sbatch hpc/submit_finetune.sh a          # extraction   -> runs/qwen_bom_lora_a_v1
sbatch hpc/submit_finetune.sh b          # configuration -> runs/qwen_bom_lora_b_v1

# --- EVAL / SERVE (need vllm — `pip install vllm` on the login node; see the note below) ---
sbatch hpc/submit_evaluate.sh a          # -> data/eval_report_qwen_bom_lora_a_v1.json
sbatch hpc/submit_evaluate.sh b
sbatch hpc/submit_serve.sh               # optional: OpenAI API on :8000, guided-json on
```

`hpc/setup_env.sh` is only for building a fresh env or topping one up — the
Aurora env is already built and has everything training needs.

> **vLLM + torch 2.13:** vLLM pins torch tightly. If `pip install vllm` tries to
> move torch 2.13, install it into a *separate* conda env used only for
> `submit_evaluate.sh` / `submit_serve.sh` (point `BOM_ENV_DIR` at it), and keep
> the training env untouched.

Smoke test before the real run (≈2 min):
`sbatch hpc/submit_finetune.sh a data.max_examples=64 train.epochs=1 train.eval_steps=10`

Trailing `key=value` tokens on `submit_finetune.sh` become config overrides.

If the env is missing `unsloth`/`vllm` (the first build only installed
torch/transformers/peft/trl), `require_pkgs` tells you; top it up on the login
node with `pip install -r requirements.txt` inside the activated env.

## GRES sizing (this cluster: `--gres=shard:N`)

| job | `--gres` | note |
|---|---|---|
| finetune | `shard:40` | 4B LoRA bf16 + Unsloth grad-checkpointing ≈ 24-40 GB. `shard:60` on CUDA OOM. |
| evaluate | `shard:20` | inference only (matches the sample eval sbatch) |
| serve | `shard:60` | vLLM reserves `serve.gpu_memory_utilization` (0.90) of what it's given |

## Evaluation gates (plan §10.2)

`evaluate.py` reads adapter kind + split from `runs/$RUN_NAME/config.resolved.json`,
generates with the trained adapter (in-process vLLM, or `--server URL`), checks:

* **adapter A** — hallucination rate **< 2 %** *(hard)* = gold says `not_specified`
  but the model asserts a value; plus `evidence_violation_rate` where the model
  supplies spans; numeric exact-match, enum accuracy, boolean F1.
* **adapter B** — body-GSM exact / within-one-catalogue-step, component-set F1,
  family accuracy.

Non-zero exit on any hard-gate failure. Report JSON at `--report-out`.

> `eval_real` currently needs regeneration — see
> `../03_DATASET/eval_real/RECOVERY_NEEDED.md`. Until then adapter-A eval falls
> back to the held-out `test` split with a warning.

## Local dev (no GPU)

```bash
pip install pyyaml pytest && pip install -e .
python -m pytest tests -q
python -m bomft.cli format --adapter a --split val -n 2
python -m bomft.cli schema --adapter b
python -m bomft.cli eval --adapter a --split test --predictions preds.jsonl
```
