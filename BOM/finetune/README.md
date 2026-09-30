# Qwen3.5 fine-tuning pipeline for the FIBC BOM generator

This trains the local Qwen3.5 checkpoint (`model_weights/`) to go directly from a
natural-language bag specification to the flat BOM CSV format used throughout
`bom_finetuning_dataset.jsonl` — the same 559 historical records the rule engine
and retrieval were built from.

This is one input into the *later* LLM-synthesis stage of the pipeline
(`app/synthesis/retry.py`'s `llm: Callable[[str], str]`). It is not a replacement
for the deterministic rule engine, and it does not change anything in `app/`.

**Running this on the SVNIT Aurora HPC cluster?** See [hpc/README.md](hpc/README.md)
for the exact folder layout to upload, the `sbatch` scripts, and cluster-specific
caveats (Slurm GRES naming, module names, home-directory quota) — the steps below
are the general/local version.

## Prerequisites

- **A complete Qwen3.5 checkpoint.** `model_weights/` in this repo currently has
  `config.json` / `tokenizer.json` / `tokenizer_config.json` / `preprocessor_config.json`
  / `model.safetensors.index.json` but **no actual `.safetensors` weight shards**.
  Point `--base-model` at wherever the full checkpoint actually lives (a completed
  local download, or a hub repo id) before running `train_qwen_bom.py` for real.
- A CUDA Linux box (or WSL2). `bitsandbytes` 4-bit quantization is not reliably
  supported on native Windows — this is why the pipeline was written and tested
  for logic only in this session, not executed here.
- `pip install -r requirements.txt`

## 1. Build the training data

```bash
python prepare_dataset.py
```

Reads `bom_finetuning_dataset_corrected.jsonl` (falls back to the non-corrected
file if that one is absent), and for every record:

- drops exact duplicate `(instruction, output)` pairs,
- parses the `output` CSV and rejects any record whose component names aren't in
  `rules/hard_constraints.json::canonical_components`, or that's missing a
  mandatory component for its `bag_type`, or whose row-sum disagrees with its own
  `GRAND TOTAL` line by more than the historical tolerance (5g, matching
  `weight_formula_tolerance_g.historical`),
- stratifies a 90/10 train/val split by `bag_type` (so a bag type like
  `two_panel`, with only 4 examples, doesn't vanish into either split by chance),
- writes `data/train.jsonl`, `data/val.jsonl`, `data/smoke.jsonl` (3-example dry
  run), `data/manifest.json` (counts), and `data/rejected.json` (what got dropped
  and why).

Each output record is `{"messages": [system, user, assistant], "meta": {...}}`.
`meta` (bag_type, ground-truth component list, ground-truth total weight) isn't
used for training — `evaluate.py` uses it to grade generations afterward.

## 2. Fine-tune

On a single 80-94GB GPU (e.g. an HPC H100), plain bf16 LoRA — no quantization —
is both simpler and higher quality than QLoRA: LoRA fine-tuning only needs
~30-50GB here, well inside 94GB, so there's no reason to pay QLoRA's 4-bit
dequantization cost or its small precision hit.

```bash
python train_qwen_bom.py \
    --base-model /path/to/complete/qwen3.5/checkpoint \
    --output-dir runs/qwen_bom_lora_v1
```

Pass `--load-in-4bit` instead only if you're on a smaller/shared GPU where
QLoRA's ~15-25GB footprint is actually needed.

- `target_modules="all-linear"` auto-targets every `nn.Linear` layer rather than
  hardcoding attention-projection names — Qwen3.5's architecture mixes
  `linear_attention` and `full_attention` layers per `config.json`, and guessing
  wrong module names would silently train nothing on most layers.
- Loss is masked to the assistant turn only via `SFTConfig(completion_only_loss=
  True)` against a `{"prompt": [...], "completion": [...]}` dataset shape (both
  as chat-message-dict lists — `build_prompt_completion_dataset` splits each
  prepared `messages` triple into system+user as the prompt and the assistant
  turn as the completion). trl applies the chat template and builds the
  completion mask internally from that split. This project originally targeted
  trl's older `DataCollatorForCompletionOnlyLM` class with a hand-derived
  response-template string; that class no longer exists as of `trl==1.9.2`
  (confirmed via `grep` against the installed package on the cluster —
  `completion_only_loss` is its replacement, and it explicitly rejects a
  flattened text field or a custom `formatting_func`, which is why the dataset
  is built this way rather than pre-rendered with `tokenizer.apply_chat_template`
  ourselves.
- `model.enable_input_require_grads()` is called explicitly whenever gradient
  checkpointing is on. This is easy to miss once QLoRA isn't in the picture:
  `prepare_model_for_kbit_training` (which normally handles this) only runs on
  the `--load-in-4bit` path, but a frozen bf16 base + LoRA + gradient
  checkpointing needs the same fix or backprop breaks on the first step.
- Defaults assume the checkpoint is genuinely vision-capable (`config.json`
  architecture is `Qwen3_5ForConditionalGeneration` with a populated
  `vision_config`), so it loads via `AutoModelForImageTextToText` by default even
  though this dataset is text-only. Pass `--model-class causal-lm` only if you're
  pointing at a text-only sibling checkpoint instead.
- Defaults are tuned for ample-VRAM full-precision LoRA: `--lora-r 32`
  `--lora-alpha 64` (more adapter capacity than the QLoRA-typical 16/32, cheap
  when you're not memory-constrained), `--optim adamw_torch_fused` (full-precision
  fused AdamW — no reason to use a paged/8-bit optimizer with headroom to spare),
  `--lr-scheduler-type cosine --warmup-ratio 0.03`, and
  `--per-device-batch-size 2 --grad-accum 8` (effective batch 16). Watch
  `nvidia-smi` during the first few steps and raise `--per-device-batch-size`
  (falling `--grad-accum` to match) if there's headroom — bigger micro-batches
  use an H100 more efficiently than more accumulation steps.
- If flash-attn is installed on the cluster, pass
  `--attn-implementation flash_attention_2` for faster/lower-memory attention;
  the default `sdpa` needs nothing extra installed.
- Once VRAM headroom is confirmed, `--no-gradient-checkpointing` trades that
  memory margin for meaningfully faster steps.

Run against `data/smoke.jsonl` first (point `--train-file`/`--val-file` at it,
`--epochs 1`) to confirm the loop runs end to end before committing GPU-hours to
the full 470-record set.

## 3. Evaluate

```bash
python evaluate.py --base-model /path/to/checkpoint --adapter-dir runs/qwen_bom_lora_v1
```

Greedy-decodes every val example and grades the output against:

- **The same hard constraints the deterministic engine is graded on** — canonical
  component vocabulary and mandatory-by-bag-type from `rules/hard_constraints.json`
  (`hard_constraints_pass_rate`). This is the number that actually matters: a
  model can write fluent CSV and still be unusable behind `synthesize_with_retry`
  if it invents a component name or drops something mandatory.
- Exact component-set match against the historical ground truth
  (`component_set_exact_match_rate`).
- Generated-total-vs-ground-truth-total relative error
  (`mean_weight_relative_error_pct`, `weight_within_5pct_rate`).
- Parse success rate (did it even emit well-formed CSV with a `GRAND TOTAL` line).

Writes a full per-example report to `data/eval_report.json` plus a printed
summary.

## What this does *not* do

- It doesn't wire the fine-tuned model into `app/synthesis/retry.py`. That
  callable expects the full JSON payload `prompt.py` builds (spec + deterministic
  BOM + retrieved examples + validation error context), not the flat
  instruction/CSV pairs this dataset uses. Treat this fine-tune as teaching the
  model the domain vocabulary and formulas first; a second SFT pass (or a
  prompt-adapter layer) matching the runtime contract is a separate follow-up
  once this one's quality bar (`hard_constraints_pass_rate`, in particular) looks
  good.
- It doesn't touch `rules/`, `app/`, or any existing dataset file.
