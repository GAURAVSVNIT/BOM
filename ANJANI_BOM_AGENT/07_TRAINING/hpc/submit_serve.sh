#!/bin/bash
# Serve both LoRA adapters behind an OpenAI-compatible vLLM endpoint with
# grammar-constrained JSON decoding (plan §9.3). Long-running.
#
#   cd ~/u24ai026/ANJANI_BOM_AGENT/07_TRAINING
#   sbatch hpc/submit_serve.sh
#   # then from the login node (node name is in the .out file):
#   ssh -L 8000:<node>:8000 <login> ; curl http://127.0.0.1:8000/health
#
# Needs vllm — if it's in a separate env:
#   BOM_ENV_DIR=$HOME/u24ai026/BOM/envs/ajani_bom_serve sbatch hpc/submit_serve.sh

#SBATCH --job-name=ajani_bom_serve
#SBATCH --partition=gpu
#SBATCH --gres=shard:60
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=08:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err
#
# vLLM reserves serve.gpu_memory_utilization (0.90) of what it's GIVEN; lower it
# (append serve.gpu_memory_utilization=0.7) for a smaller shard.

set -euo pipefail

CODE_DIR="${BOM_CODE_DIR:-$HOME/u24ai026/ANJANI_BOM_AGENT}"
ENV_DIR="${BOM_ENV_DIR:-$HOME/u24ai026/BOM/envs/ajani_bom_finetune}"
ANACONDA_MODULE="${BOM_ANACONDA_MODULE:-anaconda3-2024.2}"
BASE_MODEL="${BOM_BASE_MODEL:-$HOME/u24ai026/BOM/model_weights}"
TRAIN_DIR="$CODE_DIR/07_TRAINING"
RUN_A="${RUN_A:-qwen_bom_lora_a_v1}"
RUN_B="${RUN_B:-qwen_bom_lora_b_v1}"

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
mkdir -p logs

python -c "import vllm" 2>/dev/null || {
    echo "ERROR: vllm not in $ENV_DIR — use BOM_ENV_DIR=<serve env> sbatch hpc/submit_serve.sh" >&2
    exit 1
}

echo "[serve] node $(hostname) — tunnel:  ssh -L 8000:$(hostname):8000 <login>"
python serve.py \
    --base-model "$BASE_MODEL" \
    --adapter-a "runs/$RUN_A" \
    --adapter-b "runs/$RUN_B" \
    "$@"
