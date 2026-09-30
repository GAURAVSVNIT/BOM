"""`python -m bom_agent.cli run --enquiry file.txt [--server URL] [--json]`

Prints the BOM leading with construction type, then weight + GSM (plan H5),
then the clarification list. `--json` dumps the full PipelineResult.
"""
from __future__ import annotations
import argparse
import json
import sys
from dataclasses import asdict

from .pipeline import run


def _fmt(result) -> str:
    bs, pb = result.build_spec, result.physical_bom
    L = []
    L.append(f"CONSTRUCTION : {bs.get('family')} / {bs.get('loop_type')} loop / "
             f"top={bs.get('top_type')} / bottom={bs.get('bottom_type')}")
    tot = pb.get("grand_total_g")
    L.append(f"BAG WEIGHT   : {tot:.1f} g" if tot else "BAG WEIGHT   : (family not renderable yet)")
    L.append(f"BODY GSM     : {bs.get('body_gsm')}   belt {bs.get('belt_gpm')} gpm "
             f"@ {bs.get('belt_width_mm')} mm")
    sv = result.meta.get("solver", {})
    if sv:
        L.append(f"SOLVER       : {sv.get('mode')}  converged={sv.get('converged')}  "
                 f"passes={sv.get('passes')}  target={sv.get('target_g')}")
    L.append("")
    L.append("COMPONENTS")
    for c in pb.get("components", []):
        w = c.get("weight_g")
        L.append(f"  {c['name']:16s} {('%8.2f g' % w) if w is not None else '':>10}  "
                 f"{c.get('rule_id','')}")
    v = result.validation
    L.append("")
    L.append(f"VALIDATION   : {v['counts']}  ok={v['ok']}")
    for f in v["findings"]:
        L.append(f"  [{f['severity']}] {f['check']}: {f['message']}")
    cl = result.clarification
    L.append("")
    L.append(f"CLARIFICATIONS ({cl['n_questions']})")
    for it in cl["blocking"]:
        L.append(f"  [BLOCKING] {it['code']}: {it['question']}")
    for it in cl["advisory"]:
        L.append(f"  [advisory] {it['code']}: {it['question']}")
    for a in cl["assumptions_made"]:
        L.append(f"  [assumed]  {a['field']} = {a['value']}  ({a['reason']})")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser("bom_agent")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    g = r.add_mutually_exclusive_group(required=True)
    g.add_argument("--enquiry", help="path to an enquiry text file")
    g.add_argument("--text", help="enquiry text inline")
    r.add_argument("--server", help="vLLM server URL (omit for deterministic run)")
    r.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    text = open(a.enquiry, encoding="utf-8").read() if a.enquiry else a.text
    result = run(text, server=a.server)
    if a.json:
        print(json.dumps(asdict(result), indent=2, default=str))
    else:
        print(_fmt(result))
    # exit non-zero if any hard reject fired
    return 0 if result.validation["ok"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
