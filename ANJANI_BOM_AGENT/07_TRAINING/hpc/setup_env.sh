#!/bin/bash
# One-time environment setup for the Aurora HPC cluster (SVNIT DoCSE/AI).
#
# Back to the cluster's bundled anaconda module (python + pip + conda in one),
# not a standalone uv/pip install: this cluster has neither `pip` nor
# `curl`/`wget` on the base PATH, and no sudo to install them (confirmed —
# `apt install python3-pip` correctly refuses without root, and installing uv
# via its curl-based installer failed with "curl: command not found"). The
# anaconda module is the one self-contained toolchain actually present.
# `module avail` on this cluster shows anaconda3-2024.2 and anaconda3_new;
# anaconda3-2024.2 is used below — if it fails to load, try anaconda3_new by
# editing ANACONDA_MODULE.
#
# Run this ON THE LOGIN NODE, directly with `bash`, not `sbatch` — the manual
# says jobs may not run interactively on the master node, but installing
# packages isn't a compute job, it's the standard way every HPC user builds
# an environment before submitting anything. This has been run via `sbatch`
# by mistake twice already (that's what produced the "curl: command not
# found" and "Network is unreachable" errors — compute nodes here have no
# internet route), so this script now refuses to continue if it detects it's
# running inside a Slurm job at all.
#
# The login node's outbound bandwidth to PyPI has been observed at ~40 kB/s —
# at that rate `torch` alone (1.5-2.5GB with CUDA support) can take well over
# an hour, and a dropped SSH session partway through kills the download
# (SIGHUP -> pip's socket write fails -> "BrokenPipeError"). Run this inside
# tmux/screen so it survives a disconnected terminal:
#
#   tmux new -s bom_setup      # or: screen -S bom_setup
#   bash setup_env.sh
#   # Ctrl-b d to detach (tmux) / Ctrl-a d (screen); reattach later with:
#   tmux attach -t bom_setup   # or: screen -r bom_setup
#
# If neither tmux nor screen is available, at minimum: `nohup bash
# setup_env.sh > setup.log 2>&1 & disown`, then `tail -f setup.log`.

set -euo pipefail

if [ -n "${SLURM_JOB_ID:-}" ]; then
    echo "ERROR: this is running inside a Slurm job (SLURM_JOB_ID=$SLURM_JOB_ID) — almost" >&2
    echo "certainly submitted with 'sbatch hpc/setup_env.sh' instead of run directly." >&2
    echo "That's exactly what caused the earlier 'curl: command not found' and 'Network is" >&2
    echo "unreachable' failures: compute nodes on this cluster have no internet route, only" >&2
    echo "the login node does, and package installation needs internet either way." >&2
    echo >&2
    echo "Fix: exit this job, then on the LOGIN NODE terminal run:" >&2
    echo "    cd ~/u24ai026/ANJANI_BOM_AGENT/07_TRAINING && bash hpc/setup_env.sh" >&2
    exit 1
fi

# Env lives under ~/u24ai026/BOM/envs (kept from the first build); the code
# lives at ~/u24ai026/ANJANI_BOM_AGENT. Both are overridable.
PROJECT_DIR="${BOM_PROJECT_DIR:-$HOME/u24ai026/BOM}"  # $HOME is /home/tanmoyhazra; the project lives in the u24ai026 subfolder under it, not at $HOME itself
CODE_DIR="${BOM_CODE_DIR:-$HOME/u24ai026/ANJANI_BOM_AGENT}"
ENV_DIR="${BOM_ENV_DIR:-$PROJECT_DIR/envs/ajani_bom_finetune}"
ANACONDA_MODULE="${BOM_ANACONDA_MODULE:-anaconda3-2024.2}"  # <-- confirmed present via `module avail`; try anaconda3_new if this fails to load
REQ_FILE="$CODE_DIR/07_TRAINING/requirements.txt"

module load "$ANACONDA_MODULE"

mkdir -p "$PROJECT_DIR/envs"
if [ ! -d "$ENV_DIR" ]; then
    conda create -y -p "$ENV_DIR" python=3.11
fi

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_DIR"

# Isolate this env from two confirmed leak paths: the anaconda3-2024.2
# MODULE's own PYTHONPATH (its modulefile points python at its own base
# site-packages, which has a different/older nvidia-nccl-cu12 than what this
# env's torch needs — "undefined symbol: ncclCommResume" is what that looks
# like), and Python's default per-user site-packages (~/.local/lib/python3.11
# /site-packages, confirmed populated from earlier troubleshooting). Without
# this, `import torch` can silently resolve to the wrong nvidia/* package.
unset PYTHONPATH
export PYTHONNOUSERSITE=1

python -m pip --version  # confirms this env's own pip actually works before we rely on it

# This env's pip.conf points at an NVIDIA NGC mirror (pypi.ngc.nvidia.com) that
# does not resolve from the compute nodes — every install then burns ~10 retries
# on it. Force plain PyPI for this script and drop the bad index if we can.
export PIP_INDEX_URL="https://pypi.org/simple"
export PIP_EXTRA_INDEX_URL=""
export PIP_RETRIES=3 PIP_TIMEOUT=60
python -m pip config unset global.extra-index-url >/dev/null 2>&1 || true

python -m pip install --index-url https://pypi.org/simple --upgrade pip || true

# Generous timeout/retries for a slow link, and completed wheels land in
# pip's cache — so re-running this script after any failure only re-fetches
# what didn't finish, it doesn't restart from zero. torch is installed on its
# own first since it's by far the largest download and the most likely thing
# to hit a broken connection; the rest come after so a torch retry doesn't
# force pip to re-resolve the whole dependency set every time.
pip_install_with_retries() {
    local attempt
    for attempt in 1 2 3 4 5; do
        if python -m pip install --index-url https://pypi.org/simple \
               --timeout 120 --retries 3 "$@"; then
            return 0
        fi
        echo "pip install failed (attempt $attempt/5) — retrying in 30s..." >&2
        sleep 30
    done
    echo "ERROR: pip install kept failing after 5 attempts: $*" >&2
    return 1
}

# optional installs (non-fatal); skip with BOM_SKIP_EXTRAS=1
pip_try() {   # like pip_install_with_retries but never aborts the script
    pip_install_with_retries "$@" || {
        echo "WARN: optional install failed, continuing: $*" >&2
        return 0
    }
}

# ── 1. core training stack (REQUIRED) ────────────────────────────────────
pip_install_with_retries torch
pip_install_with_retries -r "$REQ_FILE"                 # incl. kernels, pytest, xgrammar, pyyaml
pip_install_with_retries -e "$CODE_DIR/07_TRAINING"     # the bomft package
# belt-and-suspenders in case a stale requirements.txt was synced:
pip_try kernels pytest

if [ "${BOM_SKIP_EXTRAS:-0}" != "1" ]; then
    # ── 2. Unsloth backend (OPTIONAL — model.backend=unsloth) ────────────
    #    May want to move transformers off 5.x. --upgrade-strategy only-if-needed
    #    keeps it from gratuitously changing the working stack; if it still
    #    conflicts, the WARN is printed and training on backend=hf is unaffected.
    echo; echo ">> optional: unsloth (for model.backend=unsloth)"
    pip_try --upgrade-strategy only-if-needed unsloth unsloth_zoo

    # ── 3. vLLM for eval/serve (OPTIONAL) ───────────────────────────────
    #    vLLM pins torch hard and will almost certainly downgrade torch 2.13.
    #    So it goes in a SEPARATE env by default; the eval/serve sbatch jobs
    #    use it via  BOM_ENV_DIR=$SERVE_ENV .  Set BOM_VLLM_IN_MAIN=1 to force
    #    it into this env instead (accepting the torch change).
    SERVE_ENV="${BOM_SERVE_ENV:-$PROJECT_DIR/envs/ajani_bom_serve}"
    if [ "${BOM_VLLM_IN_MAIN:-0}" = "1" ]; then
        echo; echo ">> optional: vllm into the MAIN env (will change torch)"
        pip_try vllm
    else
        echo; echo ">> optional: vllm into a separate env  $SERVE_ENV"
        if { [ -d "$SERVE_ENV" ] || conda create -y -p "$SERVE_ENV" python=3.11; } \
           && conda activate "$SERVE_ENV"; then
            unset PYTHONPATH; export PYTHONNOUSERSITE=1
            # the anaconda module's libstdc++ predates CXXABI_1.3.15 (needed by
            # vllm's sqlite3/libicu import chain) and shadows this env's own
            # newer one — give the env a modern libstdc++ and put it first.
            conda install -y -c conda-forge libstdcxx-ng || true
            export LD_LIBRARY_PATH="$SERVE_ENV/lib:${LD_LIBRARY_PATH:-}"
            python -m pip install --upgrade pip || true
            pip_try vllm xgrammar         # let vllm's resolver pull the torch it needs
            pip_try -e "$CODE_DIR/07_TRAINING"
            conda activate "$ENV_DIR"                    # back to the training env
            unset PYTHONPATH; export PYTHONNOUSERSITE=1
            echo "   -> for eval/serve:  BOM_ENV_DIR=$SERVE_ENV sbatch hpc/submit_evaluate.sh a"
        else
            echo "WARN: could not set up $SERVE_ENV — do vllm later, training is unaffected." >&2
        fi
    fi
fi

echo
echo "Environment ready at: $ENV_DIR"
echo "Sanity check (training env):"
python - <<'PY'
import torch, transformers, peft, trl
print("torch", torch.__version__, "cuda available:", torch.cuda.is_available())
print("transformers", transformers.__version__)
print("peft", peft.__version__)
print("trl", trl.__version__)
for opt in ("unsloth", "vllm", "xgrammar", "kernels", "pytest"):
    try:
        m = __import__(opt); print(opt, getattr(m, "__version__", "ok"))
    except Exception as e:
        print(opt, "MISSING —", e.__class__.__name__)
PY
