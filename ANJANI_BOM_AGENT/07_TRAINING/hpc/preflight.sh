#!/bin/bash
# Checks before you burn a GPU allocation. Safe on the login node.
#
#   cd ~/u24ai026/ANJANI_BOM_AGENT/07_TRAINING && bash hpc/preflight.sh

set -euo pipefail
_cfg=""; for _d in "$(dirname "${BASH_SOURCE[0]}")" "${SLURM_SUBMIT_DIR:-}/hpc" "${SLURM_SUBMIT_DIR:-}" "${BOM_CODE_DIR:-$HOME/u24ai026/ANJANI_BOM_AGENT}/07_TRAINING/hpc"; do [ -f "$_d/_config.sh" ] && { _cfg="$_d/_config.sh"; break; }; done; [ -n "$_cfg" ] || { echo "ERROR: hpc/_config.sh not found (set BOM_CODE_DIR)" >&2; exit 1; }; source "$_cfg"

activate_env
export BOM_BASE_MODEL="$BASE_MODEL"

echo "== package check (required for training: torch transformers peft trl datasets accelerate) =="
python - <<'PY'
req = ["torch","transformers","peft","trl","datasets","accelerate","yaml"]
opt = ["unsloth","vllm","xgrammar","bitsandbytes","kernels","pytest"]
def show(mods, tag):
    for m in mods:
        try:
            x = __import__(m); print(f"  {m:14s} {getattr(x,'__version__','ok')}  [{tag}]")
        except Exception as e:
            print(f"  {m:14s} MISSING  [{tag}]  ({e.__class__.__name__})")
show(req, "req"); show(opt, "opt: eval/serve or Unsloth backend")
PY

echo
echo "== bomft preflight (paths / dataset / configs / schema) =="
python -m bomft.cli preflight || true

echo
echo "== torch-free tests =="
if python -c "import pytest" 2>/dev/null; then
    python -m pytest tests -q
else
    echo "  (pytest not installed — 'pip install pytest' to run; not needed for training)"
fi

echo
echo "Ready to train once the [req] packages are all present:"
echo "  sbatch hpc/submit_finetune.sh a"
