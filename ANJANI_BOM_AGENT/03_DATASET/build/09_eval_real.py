# -*- coding: utf-8 -*-
"""
09_eval_real.py — the ONLY genuinely in-distribution evaluation set.

Real customer documents: the SPEC JIEXP technical data sheets, the COMPONENT
spec sheets and the scanned enquiries. These are NEVER trained on. They are the
single set that measures the actual job adapter A has to do, because every other
adapter-A row is synthesised.

Text-layer PDFs are extracted directly. Scans have no text layer and are listed
as pending OCR + hand labelling — flagged honestly rather than silently dropped.
"""
import os, sys, re, json, glob, warnings
warnings.filterwarnings("ignore")
import fitz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _bompaths import ROOT, OUT  # noqa: E402  (portable paths; see _bompaths.py)
DEST = os.path.join(OUT, "eval_real")
os.makedirs(DEST, exist_ok=True)

CANDIDATES = []
for pat in ("All_Things/SPEC JIEXP-*.pdf", "All_Things/COMPONENT C*.PDF",
            "All_Things/img*.pdf", "All_Things/Scanned Documents/*.pdf",
            "*.pdf", "BOM/BOM/*.pdf"):
    CANDIDATES += glob.glob(os.path.join(ROOT, pat))
CANDIDATES = sorted(set(CANDIDATES))

# GUARD (issue #2 / data-safety): this stage reads real customer PDFs that live
# under $BOM_ROOT/All_Things/. That tree is deliberately NOT part of the
# collected ANJANI_BOM_AGENT/ folder, so a bare run here would find nothing and
# silently truncate a good eval_real.jsonl to zero bytes. Refuse to overwrite
# unless we actually found source documents (or BOM_EVAL_FORCE=1 is set).
_existing = os.path.join(DEST, "eval_real.jsonl")
if not CANDIDATES and not os.environ.get("BOM_EVAL_FORCE"):
    have = os.path.exists(_existing) and os.path.getsize(_existing) > 0
    print("09_eval_real: no source PDFs found under", os.path.join(ROOT, "All_Things"))
    print("  BOM_ROOT =", ROOT)
    print("  This folder ships without All_Things/. Point BOM_ROOT at a tree that")
    print("  contains it, e.g.:  BOM_ROOT=/path/to/Desktop/BOM python 09_eval_real.py")
    print("  Left the existing eval_real.jsonl untouched." if have
          else "  Nothing to preserve; wrote nothing.")
    sys.exit(0 if have else 0)

# reference material, not customer enquiries — must not enter an eval set
SKIP = ("BHAVY SERVICES", "CURRICULUM", "Quotation", "Buyer's Guide",
        "Bulk Density", "BAG_TYPE_-_UPANEL", "U_Panel_Bag", "JUMBO BAG",
        "JUMBO LINER", "DocScanner", "SHANJI", "DEEPU", "SEASOM CARBON",
        "Asahi", "FIBC JUMBO")

rows, pending, agg = [], [], {"text_layer": 0, "no_text": 0, "skipped": 0}
for p in CANDIDATES:
    base = os.path.basename(p)
    if any(s.lower() in base.lower() for s in SKIP):
        agg["skipped"] += 1
        continue
    try:
        doc = fitz.open(p)
        txt = "\n".join(doc[i].get_text() for i in range(min(len(doc), 4))).strip()
        npages = len(doc)
        doc.close()
    except Exception as ex:
        pending.append({"file": os.path.relpath(p, ROOT), "reason": str(ex)})
        continue

    txt = re.sub(r"\n{3,}", "\n\n", txt)
    if len(txt) < 120:
        agg["no_text"] += 1
        pending.append({"file": os.path.relpath(p, ROOT), "pages": npages,
                        "reason": "no text layer — needs OCR then hand labelling",
                        "chars": len(txt)})
        continue

    agg["text_layer"] += 1
    # pre-fill the fields a rule reader can see; a human confirms/corrects these
    up = txt.upper()
    pre = {}
    m = re.search(r"SIZE\s*:?\s*(\d+(?:\.\d+)?)\s*[Xx]\s*(\d+(?:\.\d+)?)\s*[Xx]\s*(\d+(?:\.\d+)?)", up)
    if m:
        pre["ext_L_cm"], pre["ext_W_cm"], pre["ext_H_cm"] = [float(m.group(i)) for i in (1, 2, 3)]
    m = re.search(r"SAFE WORKING LOAD\s*:?\s*(\d+(?:\.\d+)?)", up)
    if m:
        pre["swl_kg"] = float(m.group(1))
    m = re.search(r"SAFETY FACTOR\s*:?\s*(\d)\s*:\s*(\d)", up)
    if m:
        pre["sf"] = f"{m.group(1)}:{m.group(2)}"
    m = re.search(r"(\d+)\s*(?:GR|G)/M2", up)
    if m:
        pre["stated_body_gsm"] = float(m.group(1))
    m = re.search(r"PRODUCTION LINE\s*:?\s*([A-Z0-9 \-\+]{3,24})", up)
    if m:
        pre["stated_bag_type_raw"] = m.group(1).strip()

    rows.append({
        "split": "eval_real", "adapter": "A", "style": "real_document",
        "id": "real_" + re.sub(r"\W+", "_", base)[:48],
        "source_file": os.path.relpath(p, ROOT),
        "pages": npages,
        "input": txt[:4000],
        "output_prefilled": pre,
        "output_confirmed": None,
        "meta": {"synthetic": False, "train_on_this": False,
                 "status": "PREFILLED — needs one pass of human confirmation",
                 "note": "never train on this row"},
    })

with open(os.path.join(DEST, "eval_real.jsonl"), "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
json.dump(pending, open(os.path.join(DEST, "pending_ocr.json"), "w",
                        encoding="utf-8"), indent=1)

print("=" * 78)
print("EVAL_REAL — real customer documents, never trained on")
print("=" * 78)
print(f"  candidates scanned      {len(CANDIDATES)}")
print(f"  with a text layer       {agg['text_layer']}   -> eval_real.jsonl")
print(f"  no text layer (scans)   {agg['no_text']}   -> pending_ocr.json")
print(f"  skipped (not enquiries) {agg['skipped']}")
print("\n  extracted documents:")
for r in rows:
    got = ", ".join(f"{k}={v}" for k, v in list(r["output_prefilled"].items())[:4])
    print(f"    {os.path.basename(r['source_file'])[:46]:46s} {len(r['input']):5d} ch  {got[:58]}")
print("\n  pending OCR + hand labelling:")
for p_ in pending[:12]:
    print("    " + p_["file"][:62].ljust(62) + " " + p_.get("reason","")[:34].encode("ascii","replace").decode())
print(f"\n  wrote {DEST}")
