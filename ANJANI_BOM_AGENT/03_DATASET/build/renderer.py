# -*- coding: utf-8 -*-
"""
renderer.py — minimal deterministic renderer: BuildSpec -> weight.

Not the full production renderer; enough to (a) compute the grand total from a
BuildSpec so solver-feedback rows can be generated with exact arithmetic, and
(b) serve as the phase-2 replay test against PhysicalBOM_gold.
"""
import math, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rules as R


def dims_for(family, ext, itn):
    """Pick the dimension basis the family's geometry keys off."""
    g = R.GEOMETRY.get(family)
    basis = g["basis"] if g else "EXTERNAL"
    src = ext if basis == "EXTERNAL" else itn
    if not src or any(v is None for v in src):
        src = ext or itn
    if not src or any(v is None for v in src):
        return None, basis
    return src, basis


def render(build, ext, itn):
    """Returns (lines, total_g). Every line carries its rule id."""
    fam = build.get("family")
    dd, basis = dims_for(fam, ext, itn)
    if dd is None:
        return [], None
    L, W, H = dd
    lines = []

    geo = R.GEOMETRY.get(fam)
    body_gsm = build.get("body_gsm")
    if geo and body_gsm:
        for part in ("body", "side", "top", "bottom"):
            spec = geo.get(part)
            if not spec:
                continue
            if part == "top" and build.get("top_type") not in ("TOP_PANEL",):
                continue
            gsm = {"body": body_gsm,
                   "side": body_gsm,
                   "top": build.get("top_gsm") or body_gsm,
                   "bottom": build.get("bottom_gsm") or body_gsm}[part]
            w = R.eval_dim(spec["width"], L, W, H)
            c = R.eval_dim(spec["cut"], L, W, H)
            pieces = spec["pieces"] * (2 if build.get("double_layer") and
                                       part in ("body", "side") else 1)
            wt = R.fabric_weight(gsm, w, c, pieces, spec["walls"])
            lines.append({"name": {"body": "BODY PANEL", "side": "SIDE PANEL",
                                   "top": "TOP PANEL", "bottom": "BOTTOM PANEL"}[part],
                          "gsm": gsm, "width_cm": round(w, 1), "cut_cm": round(c, 1),
                          "pieces": pieces, "walls": spec["walls"],
                          "weight_g": round(wt, 3),
                          "rule_id": f"geom.{fam}.{part}", "basis": basis})

    # baffle
    if build.get("has_baffle"):
        bg = build.get("baffle_gsm") or R.BAFFLE["gsm"]
        bw = R.eval_dim(R.BAFFLE["panel_width"], L, W, H)
        bc = R.eval_dim(R.BAFFLE["cut"], L, W, H)
        wt = R.fabric_weight(bg, bw, bc, R.BAFFLE["pieces"], 1)
        lines.append({"name": "BAFFLE", "gsm": bg, "width_cm": round(bw, 1),
                      "cut_cm": round(bc, 1), "pieces": R.BAFFLE["pieces"],
                      "weight_g": round(wt, 3), "rule_id": "geom.baffle.panel"})

    # spouts
    for tag, dia, hh, closure, gsm_key in (
            ("FILLING SPOUT", build.get("fs_dia_cm"), build.get("fs_height_cm"),
             build.get("fs_closure"), "fs"),
            ("DISCHARGE SPOUT", build.get("ds_dia_cm"), build.get("ds_height_cm"),
             build.get("ds_closure"), "ds")):
        if not dia or not hh:
            continue
        sg = build.get("spout_gsm") or 90
        cut = dia * 3.14 + 12
        base_w = hh + (5 if gsm_key == "fs" else 8)
        cl = R.CLOSURES.get(closure or "open", R.CLOSURES["open"])
        extra = eval(cl["extra_width"], {"__builtins__": {}}, {"D": dia, "H": hh})
        w = base_w + extra
        lines.append({"name": tag, "gsm": sg, "width_cm": round(w, 1),
                      "cut_cm": round(cut, 1), "pieces": 1,
                      "weight_g": round(R.fabric_weight(sg, w, cut, 1, 1), 3),
                      "rule_id": "geom.spout"})
        if cl["tie"]:
            tcut = eval(str(cl["tie"]), {"__builtins__": {}}, {"D": dia, "H": hh})
            lines.append({"name": "IRIS TIE" if closure in ("iris", "petal") else "TIE",
                          "gpm": 6, "cut_cm": round(tcut, 1),
                          "pieces": cl["tie_pieces"],
                          "weight_g": round(R.tape_weight(6, tcut, cl["tie_pieces"]), 3),
                          "rule_id": "geom.spout.tie"})

    # loops
    gpm = build.get("belt_gpm")
    if gpm:
        fh = build.get("loop_free_height_cm") or R.LOOP["default_free_height_cm"]
        LL = build.get("loop_attach_long_cm") or R.LOOP["default_LL_frac"] * H
        SL = build.get("loop_attach_short_cm") or R.LOOP["default_SL_frac"] * H
        qty = build.get("loop_qty") or 4
        cut = R.loop_cut(fh, LL, SL)
        lines.append({"name": "CORNER LOOP", "gpm": gpm, "cut_cm": round(cut, 1),
                      "pieces": qty,
                      "weight_g": round(R.tape_weight(gpm, cut, qty), 3),
                      "rule_id": "geom.loop.cut"})

    # skirt / duffle  [E, notebook p.101] — 23 kg of corpus mass
    if build.get("top_type") == "SKIRT":
        sk_w = W / 2 + 15 + W / 4 + 5
        sk_c = W * 4 + 12
        sg = build.get("top_gsm") or 90
        lines.append({"name": "SKIRT", "gsm": sg, "width_cm": round(sk_w, 1),
                      "cut_cm": round(sk_c, 1), "pieces": 1,
                      "weight_g": round(R.fabric_weight(sg, sk_w, sk_c, 1, 1), 3),
                      "rule_id": "geom.skirt"})

    # liner  [E, notebook p.86] — 46 kg of corpus mass, the largest gap
    if build.get("has_liner"):
        mic = build.get("liner_micron") or 70
        lw = 2 * W + 5
        sk_h = 0
        if build.get("top_type") == "SKIRT":
            sk_h = build.get("skirt_height_cm") or 80
        ll = H + sk_h + W / 2 + (build.get("ds_height_cm") or 0) + 15
        lines.append({"name": "LINER", "micron": mic, "width_cm": round(lw, 1),
                      "cut_cm": round(ll, 1), "pieces": 1,
                      "weight_g": round(R.liner_weight(mic, lw, ll), 3),
                      "rule_id": "geom.liner"})

    # doc pocket — flat, LDPE pouch
    if build.get("has_doc_pocket"):
        lines.append({"name": "DOC POCKET", "weight_g": 13.0,
                      "rule_id": "component.doc_pocket.flat"})

    # DDP / filler cord — seam length approximated by the bag perimeter path
    dp = build.get("dust_proof")
    if dp in ("SINGLE", "DOUBLE", "TRIPLE"):
        seam_m = (2 * (L + W) * 2 + 4 * H) / 100.0
        mult = {"SINGLE": 1, "DOUBLE": 2, "TRIPLE": 2}[dp]
        lines.append({"name": "DDP", "gpm": R.DDP_GPM,
                      "cut_cm": round(seam_m * 100, 1), "pieces": mult,
                      "weight_g": round(seam_m * mult * R.DDP_GPM, 3),
                      "rule_id": "component.ddp"})
        if dp == "TRIPLE":
            lines.append({"name": "FELT", "weight_g": round(seam_m * 8.0, 3),
                          "rule_id": "component.felt"})

    # yarn
    y = build.get("yarn_weight_g")
    if y is None:
        y = R.yarn_weight(fam, H)
    if y:
        lines.append({"name": "STITCHING", "weight_g": round(y, 3),
                      "rule_id": f"yarn.{fam}"})

    if build.get("has_label", True):
        lines.append({"name": "LABEL", "weight_g": 2.0, "rule_id": "component.label.flat"})

    total = sum(l.get("weight_g") or 0 for l in lines)
    return lines, round(total, 3)
