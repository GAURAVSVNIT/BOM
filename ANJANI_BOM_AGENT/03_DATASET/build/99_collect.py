# -*- coding: utf-8 -*-
"""
99_collect.py — gather everything produced for the new BOM architecture into
one self-contained folder.

COPIES, never moves: the originals stay where they are, and the dataset build
scripts keep working against their existing paths.
"""
import os, sys, shutil, json, hashlib, datetime, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _bompaths import ROOT  # noqa: E402

# One-time assembly script. It pulled report/analysis drafts out of a Claude
# session scratchpad that no longer exists, so it is kept for provenance only —
# it will not reproduce ANJANI_BOM_AGENT/ on a fresh machine. Override the two
# locations below if you ever need to re-run it.
SCRATCH = os.environ.get("BOM_SCRATCH", os.path.join(ROOT, "_scratch"))
DEST = os.environ.get("BOM_COLLECT_DEST", os.path.join(ROOT, "ANJANI_BOM_AGENT"))

log = collections.Counter()
missing = []


def copy_file(src, dst_dir, rename=None):
    if not os.path.exists(src):
        missing.append(src)
        log["missing"] += 1
        return None
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, rename or os.path.basename(src))
    shutil.copy2(src, dst)
    log["files"] += 1
    log["bytes"] += os.path.getsize(dst)
    return dst


def copy_tree(src, dst, ignore=None):
    if not os.path.exists(src):
        missing.append(src)
        log["missing"] += 1
        return
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*(ignore or [])))
    for dp, _, fn in os.walk(dst):
        for f in fn:
            log["files"] += 1
            log["bytes"] += os.path.getsize(os.path.join(dp, f))


if os.path.exists(DEST):
    shutil.rmtree(DEST)
os.makedirs(DEST)

# ── 01 REPORTS ──────────────────────────────────────────────────────────
d = os.path.join(DEST, "01_REPORTS")
copy_file(os.path.join(ROOT, "IMPLEMENTATION_PLAN.md"), d)
copy_file(os.path.join(ROOT, "FINAL_SYSTEM_REPORT.md"), d)
copy_file(os.path.join(ROOT, "ENGINEER_QUESTIONNAIRE.md"), d)
copy_file(os.path.join(ROOT, "dataset", "DATASET_REPORT.md"), d)

# ── 02 WEB REPORTS (the published artifacts, offline) ───────────────────
d = os.path.join(DEST, "02_WEB_REPORTS")
ARTIFACTS = [
    ("qwen-role-bom-engine.html", "1_architecture_review_where_qwen_belongs.html",
     "https://claude.ai/code/artifact/02a179b8-ecef-48f7-907a-4273cfd1ab64",
     "Where Qwen Belongs — the first architecture review"),
    ("engineer-questionnaire.html", "2_findings_and_44_questions.html",
     "https://claude.ai/code/artifact/d7822ada-65dc-4772-82fc-a0569217690b",
     "Findings from 395 sheets + the 44 questions for the engineer"),
    ("bom-system-spec.html", "3_system_spec_architecture_data_finetuning.html",
     "https://claude.ai/code/artifact/7c69d183-1307-4ef7-9cdc-29c8cb14a8fd",
     "Architecture, data preparation and fine-tuning spec"),
    ("final-report.html", "4_final_system_report.html",
     "https://claude.ai/code/artifact/b8f7d078-fc8e-4827-88a1-82744ce67626",
     "Final system report — after the engineer's answers"),
    ("impl-plan.html", "5_implementation_plan_v1.1.html",
     "https://claude.ai/code/artifact/6257cb1e-e684-4ef8-8e6e-5ff510161276",
     "Implementation plan v1.1 — build ready"),
    ("dataset-report.html", "6_dataset_report_v1.0.html",
     "https://claude.ai/code/artifact/a566fae2-3b7f-4af6-948a-1cd75ee6d180",
     "The finished fine-tuning dataset"),
]
for src, name, url, desc in ARTIFACTS:
    copy_file(os.path.join(SCRATCH, src), d, rename=name)

links = ["# Published web reports\n",
         "Each report below is published as a private Artifact on claude.ai and also",
         "saved here as a standalone HTML file you can open offline in any browser.\n",
         "| # | Report | Live link | Offline file |",
         "|---|---|---|---|"]
for i, (src, name, url, desc) in enumerate(ARTIFACTS, 1):
    links.append(f"| {i} | {desc} | [open]({url}) | `{name}` |")
links += ["", "Artifacts are private to your account unless you share them from the page's",
          "share menu. In the terminal, `/artifacts` lists them; on the web they are at",
          "<https://claude.ai/code/artifacts>.", ""]
open(os.path.join(d, "ARTIFACT_LINKS.md"), "w", encoding="utf-8").write("\n".join(links))
log["files"] += 1

# ── 03 DATASET ──────────────────────────────────────────────────────────
copy_tree(os.path.join(ROOT, "dataset"), os.path.join(DEST, "03_DATASET"),
          ignore=["__pycache__", "*.pyc"])

# ── 04 ANALYSIS (the scripts and outputs behind every number quoted) ────
d = os.path.join(DEST, "04_ANALYSIS")
scripts = ["dump_xlsx.py", "analyze.py", "gsm_test.py", "gsm_test2.py",
           "gsm_test3.py", "scan1_inventory.py", "scan2_layouts.py",
           "scan3_extract.py", "scan4_rules.py", "scan5_open.py",
           "verify_answers.py", "verify_final.py", "verify_notebook.py",
           "pdfscan.py", "pdf2.py"]
for s in scripts:
    copy_file(os.path.join(SCRATCH, s), os.path.join(d, "scripts"))
for o in ["corpus_allthings.json", "rules_out.txt", "inv1.json"]:
    copy_file(os.path.join(SCRATCH, o), os.path.join(d, "outputs"))

# ── 05 ENGINEER INPUT ───────────────────────────────────────────────────
d = os.path.join(DEST, "05_ENGINEER_INPUT")
copy_file(os.path.join(ROOT, "ENGINEER_QUESTIONNAIRE_new.md"), d,
          rename="ANSWERS_to_44_questions.md")
copy_file(os.path.join(ROOT, "Rules from Data.pdf"), d)
pages = os.path.join(SCRATCH, "rulespdf")
if os.path.isdir(pages):
    pd = os.path.join(d, "rules_pdf_pages_readable")
    os.makedirs(pd, exist_ok=True)
    for f in sorted(os.listdir(pages)):
        if f.lower().endswith(".jpg"):      # JPGs are the legible renders
            copy_file(os.path.join(pages, f), pd)

# ── 06 REFERENCE ────────────────────────────────────────────────────────
d = os.path.join(DEST, "06_REFERENCE")
copy_file(os.path.join(ROOT, "90X90X90 CM.xlsx"), d,
          rename="REFERENCE_BOM_85x85x85 (filename says 90x90x90).xlsx")
copy_file(os.path.join(ROOT, "GSM- GPM VS SWL-SF.xlsx"), d)
copy_tree(os.path.join(ROOT, "fibc"), os.path.join(d, "fibc_domain_notes"))
for f in ["Bulk Density List - National Bulk Bag.pdf",
          "Buyer's Guide to UN Certified Bulk Bags.pdf",
          "A Buyer's Guide to Purchasing Bulk Bags - National Bulk Bag.pdf"]:
    copy_file(os.path.join(ROOT, f), d)

# ── inventory ───────────────────────────────────────────────────────────
inv = []
for dp, _, fn in os.walk(DEST):
    for f in sorted(fn):
        p = os.path.join(dp, f)
        inv.append({"path": os.path.relpath(p, DEST).replace("\\", "/"),
                    "bytes": os.path.getsize(p)})
json.dump({"built": datetime.datetime.now().isoformat(timespec="seconds"),
           "root": DEST, "n_files": len(inv),
           "total_bytes": sum(x["bytes"] for x in inv),
           "missing": missing, "files": inv},
          open(os.path.join(DEST, "FOLDER_INVENTORY.json"), "w", encoding="utf-8"),
          indent=1)

print("=" * 74)
print("COLLECTED  ->", DEST)
print("=" * 74)
print(f"  files copied   {log['files']}")
print(f"  total size     {log['bytes']/1024/1024:.1f} MB")
if missing:
    print(f"  MISSING        {len(missing)}")
    for m in missing:
        print("     ", m)
else:
    print("  missing        none")
print()
for top in sorted(os.listdir(DEST)):
    p = os.path.join(DEST, top)
    if os.path.isdir(p):
        n = sum(len(f) for _, _, f in os.walk(p))
        b = sum(os.path.getsize(os.path.join(dp, f))
                for dp, _, fn in os.walk(p) for f in fn)
        print(f"  {top:24s} {n:4d} files   {b/1024/1024:7.1f} MB")
    else:
        print(f"  {top:24s}      file    {os.path.getsize(p)/1024:7.1f} KB")
