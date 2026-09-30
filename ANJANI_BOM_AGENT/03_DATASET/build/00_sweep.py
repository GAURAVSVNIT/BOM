# -*- coding: utf-8 -*-
"""
00_sweep.py — find EVERY workbook in the project, content-hash, dedupe.

Per H1: "Do not learn from duplicates. If the inquiry is the same and the
content is the same, the agent should proceed accordingly."
"""
import os, sys, json, hashlib, warnings, collections
warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _bompaths import ROOT, OUT  # noqa: E402  (portable paths; see _bompaths.py)
os.makedirs(OUT, exist_ok=True)

SKIP_DIRS = {"dataset", "__MACOSX", "__pycache__", ".git", ".pytest_cache",
             ".remember", ".vscode", "node_modules"}
XL = (".xlsx", ".xlsm")


def md5(path, chunk=1 << 20):
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


files, byext = [], collections.Counter()
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
    for fn in filenames:
        if fn.startswith("~$") or fn.startswith(".~lock"):
            continue
        p = os.path.join(dirpath, fn)
        byext[os.path.splitext(fn)[1].lower()] += 1
        if fn.lower().endswith(XL):
            files.append(p)

print("=" * 78)
print("FULL PROJECT SWEEP")
print("=" * 78)
print(f"root: {ROOT}")
print(f"total files seen: {sum(byext.values())}")
print("\nby extension (top 15):")
for e, n in byext.most_common(15):
    print(f"   {e or '(none)':10s} {n:5d}")

print(f"\nworkbooks (.xlsx/.xlsm): {len(files)}")

# ── content-hash dedupe ─────────────────────────────────────────────────
groups = collections.defaultdict(list)
bad = []
for p in files:
    try:
        groups[md5(p)].append(p)
    except Exception as ex:
        bad.append((p, str(ex)))

dupe_groups = {h: v for h, v in groups.items() if len(v) > 1}
kept = []
for h, paths in groups.items():
    # keep the shortest path (usually the canonical location), stable order
    paths_sorted = sorted(paths, key=lambda x: (len(x), x))
    kept.append({"md5": h, "keep": paths_sorted[0],
                 "duplicates": paths_sorted[1:]})

print(f"unique by content:       {len(groups)}")
print(f"duplicate groups:        {len(dupe_groups)}")
print(f"redundant copies dropped:{len(files) - len(groups)}")
if bad:
    print(f"unreadable:              {len(bad)}")

if dupe_groups:
    print("\nlargest duplicate groups:")
    for h, paths in sorted(dupe_groups.items(), key=lambda kv: -len(kv[1]))[:12]:
        rel = [os.path.relpath(p, ROOT) for p in sorted(paths, key=len)]
        print(f"   x{len(paths)}  {rel[0]}")
        for r in rel[1:]:
            print(f"          dup: {r}")

# ── where do the kept workbooks live ────────────────────────────────────
tops = collections.Counter()
for k in kept:
    rel = os.path.relpath(k["keep"], ROOT)
    tops[rel.split(os.sep)[0] if os.sep in rel else "(root)"] += 1
print("\nkept workbooks by top-level folder:")
for t, n in tops.most_common():
    print(f"   {t:22s} {n:4d}")

json.dump({"root": ROOT, "n_workbooks": len(files), "n_unique": len(groups),
           "kept": kept, "unreadable": bad},
          open(os.path.join(OUT, "sweep.json"), "w", encoding="utf-8"),
          indent=1)
print(f"\nwrote {os.path.join(OUT, 'sweep.json')}")
