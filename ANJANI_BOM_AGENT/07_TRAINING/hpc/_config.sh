#!/bin/bash
# Single source of truth for cluster paths. Sourced by every hpc/submit_*.sh
# and by hpc/preflight.sh. Override any of these by exporting it before sbatch,
# e.g.:  BOM_BASE_MODEL=/scratch/tanmoyhazra/qwen sbatch hpc/submit_finetune.sh a
#
# Aurora HPC (SVNIT DoCSE/AI) — confirmed layout:
#   - repo synced to        ~/u24ai026/ANJANI_BOM_AGENT
#   - conda env built at    ~/u24ai026/BOM/envs/ajani_bom_finetune   (by hpc/setup_env.sh)
#   - anaconda module       anaconda3-2024.2  (fallback: anaconda3_new)

CODE_DIR="${BOM_CODE_DIR:-$HOME/u24ai026/ANJANI_BOM_AGENT}"
ENV_DIR="${BOM_ENV_DIR:-$HOME/u24ai026/BOM/envs/ajani_bom_finetune}"
ANACONDA_MODULE="${BOM_ANACONDA_MODULE:-anaconda3-2024.2}"
BASE_MODEL="${BOM_BASE_MODEL:-$HOME/u24ai026/BOM/model_weights}"

TRAIN_DIR="$CODE_DIR/07_TRAINING"

# --- activate the pre-built env (login or compute node) --------------------
activate_env() {
    if [ ! -d "$ENV_DIR" ]; then
        echo "ERROR: no conda env at $ENV_DIR" >&2
        echo "Build it once on the LOGIN NODE:  bash $TRAIN_DIR/hpc/setup_env.sh" >&2
        echo "(or point BOM_ENV_DIR at an existing env)" >&2
        exit 1
    fi
    module load "$ANACONDA_MODULE"
    # shellcheck disable=SC1091
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate "$ENV_DIR"

    # Isolate from the anaconda module's own PYTHONPATH and ~/.local site-packages
    # — both leak an older nvidia-nccl-cu12 ("undefined symbol: ncclCommResume").
    unset PYTHONPATH
    export PYTHONNOUSERSITE=1
    export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
    export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"
    cd "$TRAIN_DIR"
    mkdir -p logs data
}

# --- fail early if a needed package is missing from the env ---------------
require_pkgs() {   # require_pkgs unsloth vllm
    local miss=""
    for p in "$@"; do
        python -c "import $p" 2>/dev/null || miss="$miss $p"
    done
    if [ -n "$miss" ]; then
        echo "ERROR: env at $ENV_DIR is missing:$miss" >&2
        echo "Top it up on the LOGIN NODE (env already has torch/transformers/peft/trl):" >&2
        echo "    module load $ANACONDA_MODULE" >&2
        echo "    source \"\$(conda info --base)/etc/profile.d/conda.sh\" && conda activate $ENV_DIR" >&2
        echo "    unset PYTHONPATH; export PYTHONNOUSERSITE=1" >&2
        echo "    pip install -r $TRAIN_DIR/requirements.txt" >&2
        exit 1
    fi
}
