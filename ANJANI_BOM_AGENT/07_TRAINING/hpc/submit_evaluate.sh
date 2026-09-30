#!/bin/bash
# Structural evaluation of a finished LoRA adapter (plan §10.2 gates).
#
#   cd ~/u24ai026/ANJANI_BOM_AGENT/07_TRAINING
#   sbatch hpc/submit_evaluate.sh a          # or: b
#
# RUN_NAME defaults to qwen_bom_lora_<adapter>_v1.
# Needs vllm — if it's in a separate env:
#   BOM_ENV_DIR=$HOME/u24ai026/BOM/envs/ajani_bom_serve sbatch hpc/submit_evaluate.sh a
# gres=shard:60 matches submit_finetune.sh/submit_serve.sh — vLLM's
# gpu_memory_utilization reserves a fraction of the WHOLE physical card, and a
# shard allocation smaller than that fraction gets the job killed by the
# scheduler (not a Python OOM) once vLLM actually claims the memory.
# Trailing key=value tokens override the config, e.g. on a tight/shared GPU shard:
#   sbatch hpc/submit_evaluate.sh a serve.gpu_memory_utilization=0.5

#SBATCH --job-name=ajani_bom_eval
#SBATCH --partition=gpu
#SBATCH --gres=shard:60
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

set -euo pipefail

CODE_DIR="${BOM_CODE_DIR:-$HOME/u24ai026/ANJANI_BOM_AGENT}"
ENV_DIR="${BOM_ENV_DIR:-$HOME/u24ai026/BOM/envs/ajani_bom_finetune}"
ANACONDA_MODULE="${BOM_ANACONDA_MODULE:-anaconda3-2024.2}"
BASE_MODEL="${BOM_BASE_MODEL:-$HOME/u24ai026/BOM/model_weights}"
TRAIN_DIR="$CODE_DIR/07_TRAINING"

ADAPTER="${1:-a}"; shift || true
RUN_NAME="${RUN_NAME:-qwen_bom_lora_${ADAPTER}_v1}"

if [ ! -d "$ENV_DIR" ]; then
    echo "ERROR: no conda env at $ENV_DIR" >&2; exit 1
fi

module load "$ANACONDA_MODULE"
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_DIR"
unset PYTHONPATH
export PYTHONNOUSERSITE=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
# the anaconda module's libstdc++ predates CXXABI_1.3.15 (needed by vllm's
# sqlite3/libicu import chain) and shadows the env's own newer one — put the
# env's lib dir first so it wins.
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:${LD_LIBRARY_PATH:-}"
# no CUDA toolkit (nvcc) on this cluster, only the runtime libs the wheels
# bundle — FlashInfer's top-k/top-p sampler JIT-compiles a kernel and fails
# with "Could not find nvcc"; fall back to vLLM's native sampler instead.
export VLLM_USE_FLASHINFER_SAMPLER=0

cd "$TRAIN_DIR"
mkdir -p logs data

python -c "import vllm" 2>/dev/null || {
    echo "ERROR: vllm not in $ENV_DIR. Put it in a serve env and re-run with" >&2
    echo "  BOM_ENV_DIR=\$HOME/u24ai026/BOM/envs/ajani_bom_serve sbatch hpc/submit_evaluate.sh $ADAPTER" >&2
    exit 1
}

python evaluate.py \
    --base-model "$BASE_MODEL" \
    --adapter-dir "runs/$RUN_NAME" \
    --report-out "data/eval_report_${RUN_NAME}.json" \
    "$@"
