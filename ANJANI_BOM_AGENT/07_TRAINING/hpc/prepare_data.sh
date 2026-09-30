#!/bin/bash
# Usually a no-op: when the whole ANJANI_BOM_AGENT/ repo is synced, 03_DATASET/
# sits next to 07_TRAINING/ and bomft/paths.py finds it automatically.
#
# Run this only if you deployed 07_TRAINING/ standalone (no 03_DATASET/ beside
# it): it copies the JSONL dataset + rules.py/renderer.py into 07_TRAINING/data/,
# which bomft/paths.py also auto-detects.
#
#   SRC=/path/to/ANJANI_BOM_AGENT/03_DATASET  bash hpc/prepare_data.sh

set -euo pipefail
_cfg=""; for _d in "$(dirname "${BASH_SOURCE[0]}")" "${SLURM_SUBMIT_DIR:-}/hpc" "${SLURM_SUBMIT_DIR:-}" "${BOM_CODE_DIR:-$HOME/u24ai026/ANJANI_BOM_AGENT}/07_TRAINING/hpc"; do [ -f "$_d/_config.sh" ] && { _cfg="$_d/_config.sh"; break; }; done; [ -n "$_cfg" ] || { echo "ERROR: hpc/_config.sh not found (set BOM_CODE_DIR)" >&2; exit 1; }; source "$_cfg"
HERE="$TRAIN_DIR"
SRC="${SRC:-$CODE_DIR/03_DATASET}"

if [ -d "$SRC/adapter_a" ] && [ -f "$SRC/build/rules.py" ]; then
    if [ "$(cd "$SRC/.." && pwd)" = "$CODE_DIR" ]; then
        echo "03_DATASET/ is already beside 07_TRAINING/ — nothing to do."
        echo "  dataset: $SRC"
        exit 0
    fi
fi
if [ ! -d "$SRC/adapter_a" ]; then
    echo "no dataset at $SRC — set SRC=/path/to/03_DATASET" >&2
    exit 1
fi

mkdir -p "$HERE/data"
for d in adapter_a adapter_b gold eval_real build; do
    [ -d "$SRC/$d" ] || continue
    mkdir -p "$HERE/data/$d"
    if command -v rsync >/dev/null 2>&1; then
        rsync -a --include='*/' --include='*.jsonl' --include='rules.py' \
              --include='renderer.py' --exclude='*' "$SRC/$d/" "$HERE/data/$d/"
    else
        find "$SRC/$d" \( -name '*.jsonl' -o -name 'rules.py' -o -name 'renderer.py' \) \
             -exec cp -p {} "$HERE/data/$d/" \;
    fi
done
echo "dataset -> $HERE/data/  (bomft/paths.py auto-detects it)"
find "$HERE/data" -name '*.jsonl' | sort
