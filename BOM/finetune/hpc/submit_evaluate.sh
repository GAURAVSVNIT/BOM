#!/bin/bash
# Structural evaluation of a finished LoRA adapter against the held-out val
# set. Run after submit_finetune.sh's job has completed.
#
#   cd ~/u24ai026/BOM/finetune
#   sbatch hpc/submit_evaluate.sh
#
# Edit RUN_NAME below to match --output-dir from submit_finetune.sh if you
# change it there.

#SBATCH --job-name=ajani_bom_eval
#SBATCH --partition=gpu
#SBATCH --gres=shard:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

set -euo pipefail

PROJECT_DIR="$HOME/u24ai026/BOM"  # $HOME is /home/tanmoyhazra; the project lives in the u24ai026 subfolder under it
ENV_DIR="$PROJECT_DIR/envs/ajani_bom_finetune"
RUN_NAME="qwen_bom_lora_v1"
ANACONDA_MODULE="anaconda3-2024.2"  # <-- must match what you used in setup_env.sh

# Absolute cd regardless of what directory `sbatch` was invoked from — makes
# evaluate.py's own relative --adapter-dir/--report-out args resolve
# correctly even if this got submitted from the wrong place.
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

python evaluate.py \
    --base-model "$PROJECT_DIR/model_weights" \
    --adapter-dir "runs/$RUN_NAME" \
    --report-out "data/eval_report_${RUN_NAME}.json"
