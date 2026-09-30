#!/bin/bash
# Full LoRA fine-tune on a single Aurora H100 (94GB) — plain bf16 LoRA, no
# quantization (see finetune/README.md for why). Submit only after
# submit_smoke_test.sh has completed cleanly.
#
#   cd ~/u24ai026/BOM/finetune
#   mkdir -p logs runs
#   sbatch hpc/submit_finetune.sh
#   squeue -u $USER
#   tail -f logs/ajani_bom_lora_<JOBID>.out
#
# GRES CAVEAT: the cluster manual's own sample scripts request
# `--gres=shard:1`. I have no way to confirm from here whether one "shard"
# unit is a full H100 or a fractional MIG slice on this specific cluster —
# after your first job starts, check the GPU memory actually visible to it
# (the nvidia-smi line below prints this) and compare against the full 94GB.
# If it's less, ask support.hpc@coed.svnit.ac.in what GRES value gets you a
# whole GPU, or try `--gres=shard:4` / `--gres=gpu:1` as alternates.

#SBATCH --job-name=ajani_bom_lora
#SBATCH --partition=gpu
#SBATCH --gres=shard:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=24:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

set -euo pipefail

PROJECT_DIR="$HOME/u24ai026/BOM"  # $HOME is /home/tanmoyhazra; the project lives in the u24ai026 subfolder under it
ENV_DIR="$PROJECT_DIR/envs/ajani_bom_finetune"
RUN_NAME="qwen_bom_lora_v1"
ANACONDA_MODULE="anaconda3-2024.2"  # <-- must match what you used in setup_env.sh

# Absolute cd regardless of what directory `sbatch` was invoked from — makes
# train_qwen_bom.py's own relative --output-dir arg resolve correctly even if
# this got submitted from the wrong place.
cd "$PROJECT_DIR/finetune"

if [ ! -d "$ENV_DIR" ]; then
    echo "ERROR: no conda env at $ENV_DIR — run 'bash hpc/setup_env.sh' on the login node first." >&2
    exit 1
fi

module load "$ANACONDA_MODULE"
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_DIR"

# Isolate from the anaconda module's own PYTHONPATH and Python's per-user
# site-packages — both confirmed to leak a different/older nvidia-nccl-cu12
# in here, which is what "undefined symbol: ncclCommResume" was.
unset PYTHONPATH
export PYTHONNOUSERSITE=1

echo "=== GPU visible to this job ==="
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv
echo "==="

python train_qwen_bom.py \
    --base-model "$PROJECT_DIR/model_weights" \
    --output-dir "runs/$RUN_NAME"

echo "Adapter saved to $(pwd)/runs/$RUN_NAME"
