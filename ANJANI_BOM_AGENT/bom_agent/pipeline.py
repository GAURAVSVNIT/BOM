"""Wires stages 0-9 (plan §2). One call: enquiry text -> PipelineResult.

    from bom_agent.pipeline import run
    result = run(enquiry_text)                      # deterministic, no GPU
    result = run(enquiry_text, server="http://127.0.0.1:8000")   # with the adapters
"""
from __future__ import annotations

from .contracts import PipelineResult
from .extract import extract
from .classify import classify, derive_swl
from .retrieve import retrieve
from .envelope import envelope
from .configure import configure
from .solve import solve
from .validate import validate
from .clarify import build_clarification


def _client(server: str | None):
    if not server:
        return None
    from bomft.serve import HttpClient          # 07_TRAINING package
    c = HttpClient(server)
    if not c.health():
        raise RuntimeError(f"vLLM server at {server} is not healthy")
    return c


def run(enquiry_text: str, server: str | None = None) -> PipelineResult:
    client = _client(server)
    flags: list[str] = []

    # 1 · extract
    o = extract(enquiry_text, client=client)
    o_dict = o.to_dict()

    # 2 · classify + derive
    cls = classify(o)
    swl, swl_note = derive_swl(o)
    if swl_note:
        flags.append(swl_note)

    # 3 · retrieve
    retrieved = retrieve(o_dict, cls["family"], k=3)

    # 4 · envelope
    loop_qty = o.val("loop_qty") or 4
    env = envelope(o_dict, cls["family"], cls["loop_type"], loop_qty)

    # 5 · configure (adapter B)
    build_spec, cflags = configure(o_dict, cls, retrieved, env, client=client)
    flags += cflags
    bs = build_spec.to_dict()
    bs.setdefault("family", cls["family"])
    bs.setdefault("loop_type", cls["loop_type"])
    bs.setdefault("top_type", cls["top_type"])
    bs.setdefault("bottom_type", cls["bottom_type"])

    # 6 + 7 · render + solve (solve renders internally)
    solved = solve(bs, o_dict, env)
    final_bs = solved["build_spec"]
    pbom = solved["physical_bom"]
    if solved.get("clarification"):
        flags.append(solved["clarification"]["question"])

    # 8 · validate
    v = validate(final_bs, o_dict, pbom, env)

    # 9 · clarification list
    cl = build_clarification(o, cls, final_bs, env, extra_flags=flags)

    return PipelineResult(
        order_spec=o_dict,
        build_spec=final_bs,
        physical_bom=pbom,
        clarification=cl.to_dict(),
        validation=v,
        meta={
            "used_model": client is not None,
            "classification": cls,
            "envelope": env,
            "retrieved_sources": [r.get("source") for r in retrieved],
            "solver": {k: solved[k] for k in ("mode", "converged", "passes",
                                              "target_g", "history") if k in solved},
            "presentation_order": ["construction_type", "bag_weight_and_gsm", "rest"],
        },
    )
