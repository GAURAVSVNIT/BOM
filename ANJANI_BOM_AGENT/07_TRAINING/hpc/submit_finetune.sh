#!/bin/bash
# LoRA fine-tune one adapter (plan §9). Run after the env is built.
#
#   cd ~/u24ai026/ANJANI_BOM_AGENT/07_TRAINING
#   sbatch hpc/submit_finetune.sh a          # extraction   (adapter A)
#   sbatch hpc/submit_finetune.sh b          # configuration (adapter B)
#
# Tokens after the adapter go to finetune.py as config overrides, e.g.:
#   sbatch hpc/submit_finetune.sh b train.epochs=3
# Smoke test (~2 min):
#   sbatch hpc/submit_finetune.sh a data.max_examples=64 train.epochs=1 train.eval_steps=10

#SBATCH --job-name=ajani_bom_ft
#SBATCH --partition=gpu
#SBATCH --gres=shard:60
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err
#
# --gres: fractional GPU via `shard:N`. bf16 LoRA + grad-checkpointing:
#   4B base  -> ~24-40 GB   (shard:40 enough) ;  8-9B base -> ~40-56 GB
# CUDA OOM -> bump to shard:80, or QLoRA: add `model.load_in_4bit=true` to the args.

set -euo pipefail

# --- self-contained config (no external `source`; sbatch spools the script) ---
CODE_DIR="${BOM_CODE_DIR:-$HOME/u24ai026/ANJANI_BOM_AGENT}"
ENV_DIR="${BOM_ENV_DIR:-$HOME/u24ai026/BOM/envs/ajani_bom_finetune}"
ANACONDA_MODULE="${BOM_ANACONDA_MODULE:-anaconda3-2024.2}"
BASE_MODEL="${BOM_BASE_MODEL:-$HOME/u24ai026/BOM/model_weights}"
TRAIN_DIR="$CODE_DIR/07_TRAINING"

ADAPTER="${1:-a}"; shift || true
RUN_NAME="${RUN_NAME:-qwen_bom_lora_${ADAPTER}_v1}"

if [ ! -d "$ENV_DIR" ]; then
    echo "ERROR: no conda env at $ENV_DIR — run 'bash hpc/setup_env.sh' on the login node." >&2
    exit 1
fi

module load "$ANACONDA_MODULE"
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_DIR"

# isolate from the anaconda module's PYTHONPATH + ~/.local (leaked old nvidia-nccl-cu12)
unset PYTHONPATH
export PYTHONNOUSERSITE=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"

cd "$TRAIN_DIR"
mkdir -p logs data

miss=""
for p in transformers peft trl datasets accelerate; do
    python -c "import $p" 2>/dev/null || miss="$miss $p"
done
if [ -n "$miss" ]; then
    echo "ERROR: env $ENV_DIR is missing:$miss  (pip install -r requirements.txt in the env)" >&2
    exit 1
fi

echo "[ft] node=$(hostname)  env=$ENV_DIR  base=$BASE_MODEL  adapter=$ADAPTER  run=$RUN_NAME"
python finetune.py \
    --adapter "$ADAPTER" \
    --base-model "$BASE_MODEL" \
    --output-dir "runs/$RUN_NAME" \
    "$@"

echo "[done] adapter $ADAPTER -> $TRAIN_DIR/runs/$RUN_NAME"
