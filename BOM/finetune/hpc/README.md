# Running the fine-tune on the Aurora HPC cluster (SVNIT DoCSE/AI)

Based on the cluster's own "HPC Cluster User Manual" (Aurora: 2 nodes, 1× NVIDIA
H100 94GB each, 320 CPU cores, 5120GB RAM, Ubuntu 22.04, Slurm scheduler, master
node `172.21.0.10`) and what's actually been confirmed on the live cluster so
far. Two real gotchas already surfaced there — read this whole file, not just
section 1, before running anything again.

**Account layout, confirmed from your own terminal session:** the SSH login
user is `tanmoyhazra` (`$HOME` = `/home/tanmoyhazra` — proved by `cd ..` four
times from `~/u24ai026/BOM/finetune/hpc` landing exactly on `~`, then one more
`cd ..` landing on `/home`). `u24ai026` is a **subfolder inside that home
directory**, not a separate account — this matches the manual's own rule that
student/scholar accounts are requested by the advisor, so the cluster account
is `tanmoyhazra`'s and your project lives inside it. The project root is
therefore `~/u24ai026/BOM` (i.e. `/home/tanmoyhazra/u24ai026/BOM`), and every
`ssh`/`scp` example below logs in as `tanmoyhazra`, not `u24ai026`.

## 0. `setup_env.sh` must run on the login node, never via `sbatch`

This bears repeating because it caused two different, confusing-looking
failures back to back — `curl: command not found`, then (after switching to
conda) `CondaHTTPError` / `Network is unreachable` — that were actually the
*same* root cause both times: `setup_env.sh` was submitted with `sbatch`
instead of run directly, so it executed inside a Slurm job on a compute node.
Compute nodes on this cluster have **no internet route at all** (that's what
"Network is unreachable", not a timeout, means), while the login node does —
and package installation needs internet regardless of whether it's `curl`,
`pip`, or `conda` doing the fetching.

`setup_env.sh` now checks for `$SLURM_JOB_ID` and refuses to run at all if
it detects it's inside a job, so this fails loudly and immediately instead of
burning through conda's retry loop. If you see that error, exit the job and
run it directly on the login node instead:

```bash
cd ~/u24ai026/BOM/finetune
bash hpc/setup_env.sh
```

Re-upload `hpc/setup_env.sh` first if the copy on the cluster predates this
check (command in section 2).

## 1. What to upload, and where

Don't upload the whole local `BOM/` folder — it has ~190 raw Excel files, old
demo `runs/`, and reference-only folders (`bom_rules/`, `more_rules/`) that
have nothing to do with fine-tuning. Upload only this, landing at
`~/u24ai026/BOM/` (i.e. `/home/tanmoyhazra/u24ai026/BOM/`) on the cluster:

```
~/u24ai026/BOM/                           (under $HOME = /home/tanmoyhazra;
│                                           home quota is 100GB, extendable to
│                                           500GB on request per the manual's FAQ —
│                                           check this is enough once you know the
│                                           checkpoint size)
├── envs/                                 <- created by setup_env.sh, don't upload
├── rules/
│   ├── hard_constraints.json             <- from local BOM/rules/ (evaluate.py needs this)
│   ├── defaults.json
│   └── heuristics.json
├── model_weights/                        <- upload your COMPLETE Qwen3.5 checkpoint here:
│   ├── config.json                          config.json, tokenizer.json, tokenizer_config.json,
│   ├── tokenizer.json                       preprocessor_config.json, model.safetensors.index.json,
│   ├── tokenizer_config.json                 AND the actual model-*.safetensors shard files
│   ├── preprocessor_config.json              (the local BOM/model_weights/ only has the first five —
│   ├── model.safetensors.index.json          that's the gap this upload fills)
│   └── model-000XX-of-000YY.safetensors
└── finetune/                             <- upload this whole folder from local BOM/finetune/
    ├── bom_csv.py
    ├── prepare_dataset.py
    ├── train_qwen_bom.py
    ├── evaluate.py
    ├── requirements.txt
    ├── data/
    │   ├── train.jsonl
    │   ├── val.jsonl
    │   ├── smoke.jsonl
    │   ├── manifest.json
    │   └── rejected.json
    ├── runs/                             <- empty; LoRA checkpoints land here after training
    ├── logs/                             <- empty; must exist before the first `sbatch` (Slurm
    │                                        will not create it and the job dies immediately if missing)
    └── hpc/
        ├── setup_env.sh
        ├── submit_smoke_test.sh
        ├── submit_finetune.sh
        ├── submit_evaluate.sh
        └── README.md                     (this file)
```

This is deliberately the same relative layout as the local repo
(`finetune/train_qwen_bom.py`'s default `--base-model` is `../model_weights`,
`evaluate.py`'s rulebook path is `../rules/hard_constraints.json`), just with
that whole `BOM/` tree sitting inside `~/u24ai026/` instead of at `$HOME`
directly — so none of the Python scripts need path edits, only `RUN_NAME` at
the top of `submit_finetune.sh`/`submit_evaluate.sh` if you rename a run.

## 2. Upload it (from Windows PowerShell — ships with `scp.exe` via OpenSSH)

```powershell
ssh tanmoyhazra@172.21.0.10 "mkdir -p ~/u24ai026/BOM/finetune/logs ~/u24ai026/BOM/finetune/runs ~/u24ai026/BOM/model_weights"

scp -r "D:\CODING\Ajani_Interweave_Automation\BOM\rules" tanmoyhazra@172.21.0.10:~/u24ai026/BOM/
scp -r "D:\CODING\Ajani_Interweave_Automation\BOM\finetune" tanmoyhazra@172.21.0.10:~/u24ai026/BOM/
scp -r "\path\to\complete\qwen3.5\checkpoint\*" tanmoyhazra@172.21.0.10:~/u24ai026/BOM/model_weights/
```

Re-run the `scp -r ... finetune` line any time you get updated `.sh`/`.py`
files from this conversation — `scp -r` overwrites the destination folder's
contents, so it's safe to re-upload the whole `finetune/` directory repeatedly
as it's revised (your `runs/`/`logs/` output from earlier attempts on the
cluster will survive, since the local source doesn't have those populated).

The checkpoint is likely tens of GB — expect this to take a while, and prefer
uploading it directly from wherever you downloaded it rather than round
tripping through this Windows machine if avoidable. MobaXterm's GUI (drag files
into the left-panel file browser) works the same way and is what the manual
itself walks through for Windows users, if you'd rather not use the command
line for the large transfer.

## 3. One-time environment setup (on the login node, not via sbatch)

```bash
ssh tanmoyhazra@172.21.0.10
cd ~/u24ai026/BOM/finetune
tmux new -s bom_setup      # survives a dropped SSH session — see below
bash hpc/setup_env.sh
```

Detach with `Ctrl-b d` once it's running (it keeps going in the background);
reattach later with `tmux attach -t bom_setup`. This matters here specifically:
the login node's bandwidth to PyPI has been observed at ~40 kB/s, so `torch`
alone can take over an hour to download, and a run outside tmux/screen dies
the moment your terminal disconnects (`BrokenPipeError` — the SSH session
drops, `bash` gets `SIGHUP`, `pip`'s socket write fails mid-download). If
`tmux` isn't available, `screen -S bom_setup` works the same way; failing
that, `nohup bash hpc/setup_env.sh > setup.log 2>&1 & disown` and `tail -f
setup.log`. The script itself now also retries each `pip install` up to 5
times with a longer timeout, and installs `torch` on its own first (the
biggest download) so a retry doesn't force re-resolving every other package —
already-completed wheels stay in pip's cache, so re-running the whole script
after any failure resumes rather than starting over.

This uses the cluster's bundled `anaconda3-2024.2` module (confirmed present
via `module avail`), not a standalone `uv`/`pip`. An earlier draft tried `uv`
to avoid the module-name guessing game entirely, but this cluster has neither
`pip` nor `curl`/`wget` on the base PATH and no sudo to install them (`apt
install python3-pip` correctly refuses without root; `uv`'s curl-based
installer fails with `curl: command not found`) — so the anaconda module,
which bundles its own python/pip/conda, is the one self-contained toolchain
that's actually usable here. If `module load anaconda3-2024.2` itself fails,
try `anaconda3_new` instead (edit `ANACONDA_MODULE` at the top of
`setup_env.sh` and each `submit_*.sh`).

pip itself doesn't shell out to `curl`/`wget` (it has its own HTTP client), so
once the anaconda module gives you a working `pip`, installing
`torch`/`transformers`/`peft`/`trl` from PyPI will work as long as the login
node has outbound internet — which it must, for `module avail`/cluster
software to have gotten there in the first place.

## 4. Run order

```bash
cd ~/u24ai026/BOM/finetune

# 1. cheap dry run — catches env/path/module problems in ~minutes, not hours
sbatch hpc/submit_smoke_test.sh
squeue -u $USER
tail -f logs/ajani_bom_smoke_<JOBID>.out

# 2. once that finishes clean, the real fine-tune
sbatch hpc/submit_finetune.sh
squeue -u $USER
tail -f logs/ajani_bom_lora_<JOBID>.out

# 3. once training finishes, grade the adapter
sbatch hpc/submit_evaluate.sh
tail -f logs/ajani_bom_eval_<JOBID>.out
```

Pull the results back down to Windows when done:

```powershell
scp -r tanmoyhazra@172.21.0.10:~/u24ai026/BOM/finetune/runs/qwen_bom_lora_v1 "D:\CODING\Ajani_Interweave_Automation\BOM\finetune\runs\"
scp tanmoyhazra@172.21.0.10:~/u24ai026/BOM/finetune/data/eval_report_qwen_bom_lora_v1.json "D:\CODING\Ajani_Interweave_Automation\BOM\finetune\data\"
```

## 5. The one thing I genuinely can't confirm from here: `--gres=shard:1`

Every Slurm GPU example in the cluster manual requests `--gres=shard:1` — that's
a cluster-specific GRES resource name, not the generic `gpu:1` most Slurm docs
use, so I kept it as-is rather than guess-substituting something more familiar.
What I *can't* tell without actually running on Aurora is whether one `shard`
unit is a full 94GB H100 or a fractional MIG slice of one. The training script
prints the GPU's total memory at the start of every job
(`nvidia-smi --query-gpu=... --format=csv` line near the top of each log) —
check that reads close to 94GB. If it reads much lower, you're on a slice, not
the whole card: bf16 LoRA needs ~30-50GB, so a small slice may not be enough.
In that case, ask support.hpc@coed.svnit.ac.in what GRES value gets you a
whole GPU, or try `--gres=shard:4` / `--gres=gpu:1` as alternates in the
`submit_*.sh` files.

Also note the manual's own sample scripts have a typo worth knowing about if
you ever read the PDF directly — several `#SBATCH` lines in it use a
typographic en-dash (`–error=`, `–partition=gpu`) instead of a real
double-hyphen (`--error=`, `--partition=gpu`), which would fail if copy-pasted
verbatim. The scripts here use the correct `--` throughout.
