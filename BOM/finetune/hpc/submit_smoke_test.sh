#!/bin/bash
# Cheap end-to-end dry run on the 3-example smoke set. Submit this BEFORE the
# real training job to catch environment/path/module problems without burning
# real GPU time:
#
#   cd ~/u24ai026/BOM/finetune
#   mkdir -p logs runs
#   sbatch hpc/submit_smoke_test.sh
#   squeue -u $USER
#
# Relative paths below (logs/, data/, runs/) are resolved against the
# directory sbatch was invoked FROM, so submit from ~/u24ai026/BOM/finetune, not from
# hpc/.

#SBATCH --job-name=ajani_bom_smoke
#SBATCH --partition=gpu
#SBATCH --gres=shard:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=00:30:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

set -euo pipefail

PROJECT_DIR="$HOME/u24ai026/BOM"  # $HOME is /home/tanmoyhazra; the project lives in the u24ai026 subfolder under it
ENV_DIR="$PROJECT_DIR/envs/ajani_bom_finetune"
ANACONDA_MODULE="anaconda3-2024.2"  # <-- must match what you used in setup_env.sh

# Absolute cd regardless of what directory `sbatch` was invoked from — makes
# train_qwen_bom.py's own relative data/runs args resolve correctly even if
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
    --train-file data/smoke.jsonl \
    --val-file data/smoke.jsonl \
    --output-dir runs/smoke_test \
    --epochs 1 \
    --per-device-batch-size 1 \
    --grad-accum 1
