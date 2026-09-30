# -*- coding: utf-8 -*-
"""
rules.py — the locked Anjani rule book, as data.

Every constant traces to IMPLEMENTATION_PLAN.md. Provenance codes:
    E   engineer's ruling (questionnaire answers / Rules-from-Data PDF / notebook)
    D   derived from the corpus and confirmed
    E+D both agree
Rule levels: hard_constraint | default_preference | historical_variant
"""
import math, re

# ═══════════════════ 1. taxonomy ════════════════════════════════════════
FAMILY_PATTERNS = [
    ("four_panel_baffle", r"BAFFLE|Q[\s\-]*BAG"),
    ("container_liner",   r"CONTAINER"),
    ("omega",             r"OMEGA"),
    ("tunnel",            r"TUNNEL"),
    ("hood",              r"HOOD|I[\s\-]*BAG|H\s*BOTTOM"),
    ("platten",           r"PLATTEN|PLATTERN|SLING"),
    ("box",               r"\bBOX\b"),
    ("conical",           r"CONICAL|CANICAL"),
    ("pinch_corner",      r"PINCH|PINTCH"),
    ("single_loop",       r"SINGLE\s*LOOP|\b1\s*LOOP\b"),
    ("two_loop",          r"\b2\s*LOOP|TWO\s*LOOP|DOUBLE\s*LOOP"),
    # "C-TYPE" / "C TYPE" only. The reversed "TYPE C" / "TYPE-C" was removed: it
    # collides with the Type-C static-protection class label (§1.12), so a bag
    # described "U-PANEL, STATIC TYPE C" no longer misclassifies as two_panel.
    ("two_panel",         r"\b2[\s\-]*PANN?EL|TWO\s*PANN?EL|\bC[\s\-]*TYPE\b"),
    ("u_panel",           r"U\s*\+\s*2|U[\s\-]*PANN?EL|UPANN?EL|U\+2"),
    ("circular",          r"CIRCULAR|TUBELAR|TUBULAR|CIRCULER"),
    ("four_panel",        r"\b4[\s\-]*PANN?EL|FOUR\s*PANN?EL"),
]
FAMILIES = ["u_panel", "circular", "four_panel", "four_panel_baffle", "two_panel",
            "single_loop", "two_loop", "omega", "tunnel", "pinch_corner",
            "box", "hood", "platten", "container_liner", "conical", "other"]

DEFAULT_FAMILY = "u_panel"          # [E, A1] house default
CIRCULAR_BELT_MM = 70               # [E, A1] belt >= 70 mm -> circular
CROSS_CORNER_MIN_MM = 70            # [E, A2] 70-100 mm -> cross corner
CROSS_CORNER_MAX_MM = 100


def classify_family(raw_text: str, belt_width_mm=None) -> tuple[str, str]:
    """Returns (family, provenance)."""
    s = re.sub(r"\s+", " ", (raw_text or "")).upper()
    for fam, pat in FAMILY_PATTERNS:
        if re.search(pat, s):
            return fam, "stated"
    if belt_width_mm and belt_width_mm >= CIRCULAR_BELT_MM:
        return "circular", "inferred_from_belt_width"
    return DEFAULT_FAMILY, "house_default"


def classify_loop_type(raw_text: str, belt_width_mm=None) -> tuple[str, str]:
    s = re.sub(r"\s+", " ", (raw_text or "")).upper()
    if "CROSS" in s:
        return "cross_corner", "stated"
    if "FULL" in s and "LOOP" in s:
        return "full_running", "stated"
    if "SINGLE LOOP" in s:
        return "single", "stated"
    if "CORNER" in s:
        return "corner", "stated"
    if belt_width_mm and CROSS_CORNER_MIN_MM <= belt_width_mm <= CROSS_CORNER_MAX_MM:
        return "cross_corner", "inferred_from_belt_width"
    return "corner", "house_default"


# ═══════════════════ 2. weight formulas [E+D, hard] ═════════════════════
def fabric_weight(gsm, width_cm, cut_cm, pieces=1, walls=1):
    """W1"""
    return gsm * width_cm * cut_cm * pieces * walls / 10000.0


def tape_weight(gpm, cut_cm, pieces=1):
    """W2 — GPM is grams per METRE, linear"""
    return gpm * cut_cm * pieces / 100.0


def liner_weight(micron, width_cm, length_cm):
    """W3 — micron x L x W x 2 x 0.92 / 10000"""
    return micron * width_cm * length_cm * 2 * 0.92 / 10000.0


# ═══════════════════ 3. geometry [E, hard] ══════════════════════════════
# dimension_basis: which dimension set the family's cut sizes key off.
GEOMETRY = {
    "u_panel": {
        "basis": "EXTERNAL",
        "body":   {"width": "W+8", "cut": "2*H+L+8", "pieces": 1, "walls": 1},
        "side":   {"width": "L+8", "cut": "H+8",     "pieces": 2, "walls": 1},
        "top":    {"width": "L+8", "cut": "W+8",     "pieces": 1, "walls": 1},
        "bottom": None, "reinforcement": None,
    },
    "box": {   # notebook p.71 — identical to u_panel, verified on his example
        "basis": "EXTERNAL",
        "body":   {"width": "W+8", "cut": "2*H+L+8", "pieces": 1, "walls": 1},
        "side":   {"width": "L+8", "cut": "H+8",     "pieces": 2, "walls": 1},
        "top":    None, "bottom": None, "reinforcement": None,
    },
    "circular": {
        "basis": "EXTERNAL",
        "body":   {"width": "W+L", "cut": "H+8", "pieces": 1, "walls": 2},
        "top":    {"width": "L+10", "cut": "W+10", "pieces": 1, "walls": 1},
        "bottom": {"width": "L+10", "cut": "W+10", "pieces": 1, "walls": 1},
        "side": None, "reinforcement": None,
    },
    "pinch_corner": {
        "basis": "INTERNAL",
        "body":   {"width": "W+L", "cut": "H+12", "pieces": 1, "walls": 2},
        "top":    {"width": "W+12", "cut": "W+12", "pieces": 1, "walls": 1},
        "bottom": {"width": "W+12", "cut": "W+12", "pieces": 1, "walls": 1},
        "side": None, "reinforcement": None,
    },
    "four_panel_baffle": {
        "basis": "INTERNAL",        # [E, notebook p.61] explicit exception
        "body":   {"width": "W+8", "cut": "H+8", "pieces": 4, "walls": 1},
        "top":    {"width": "L+8", "cut": "W+8", "pieces": 1, "walls": 1},
        "bottom": {"width": "L+8", "cut": "W+8", "pieces": 1, "walls": 1},
        "side": None, "reinforcement": None,
    },
    "four_panel": {
        "basis": "EXTERNAL",
        "body":   {"width": "W+8",  "cut": "H+8",  "pieces": 4, "walls": 1},
        "top":    {"width": "L+10", "cut": "W+10", "pieces": 1, "walls": 1},
        "bottom": {"width": "L+8",  "cut": "W+8",  "pieces": 1, "walls": 1},
        "side": None, "reinforcement": None,
    },
    "two_panel": {
        "basis": "INTERNAL",
        "side":   {"width": "2*W+12", "cut": "H+12", "pieces": 2, "walls": 1},
        "body": None, "top": None, "bottom": None, "reinforcement": None,
    },
    "tunnel": {
        "basis": "EXTERNAL",
        "side":   {"width": "W+7", "cut": "H+7", "pieces": 2, "walls": 1},
        "body": None, "top": None, "bottom": None, "reinforcement": None,
    },
    "container_liner": {
        "basis": "EXTERNAL",
        "body":   {"width": "W+16", "cut": "2*L+2*H+16", "pieces": 1, "walls": 1},
        "side":   {"width": "H+16", "cut": "L+16", "pieces": 2, "walls": 1},
        "top": None, "bottom": None, "reinforcement": None,
    },
    "platten": {
        "basis": "EXTERNAL",
        "bottom": {"width": "W+8", "cut": "W+8", "pieces": 1, "walls": 1},
        "body": None, "side": None, "top": None, "reinforcement": None,
    },
}
# omega, hood, conical, single_loop, two_loop carry order-specific inputs and
# are handled by dedicated builders rather than a flat width/cut pair.

BAFFLE = {                                   # [E, notebook p.59/60/67]
    "panel_width": "sqrt((L/3)**2+(W/3)**2)+7",   # corner baffle
    "center_panel_width": "W+7",
    "cut": "H-20",                                # 10 cm off top and bottom
    "pieces": 4,
    "fabric_width": "W+12",                       # marked (W/3+6)|W/3|(W/3+6)
    "gsm": 120,                                   # 15+90+15 both-side laminated
    "punch_patch_cm": (10, 30),
    "punch_gpm_basis": "GSM*10*30*(holes*4)/10000",
    "patterns": ["4_BAFFLE", "CENTER_BAFFLE", "2_BAFFLE", "2_BAFFLE_PLUS_CENTER"],
    "punch_types": ["NORMAL", "OVAL"],
}


def eval_dim(expr, L, W, H):
    return eval(expr, {"__builtins__": {}, "sqrt": math.sqrt, "math": math},
                {"L": L, "W": W, "H": H})


# ═══════════════════ 4. spouts and closures [E, hard] ═══════════════════
SPOUT = {
    "cut_single_fold": "D*3.14+12",
    "cut_double_fold": "D*3.14+15",
    "fs_width": "H+5",
    "ds_width": "H+8",
}
CLOSURES = {
    "open":   {"extra_width": "0",       "tie": None,             "tie_pieces": 0},
    "tied":   {"extra_width": "H+8",     "tie": "125",            "tie_pieces": 1},
    "iris":   {"extra_width": "D/2+6",   "tie": "D*3.14+38",      "tie_pieces": 2},
    "petal":  {"extra_width": "0",       "tie": "D*3.14+38",      "tie_pieces": 2,
               "extras": ["DS FLAP", "DS PATCH"], "flap": "D/1.42"},
    "pyjama": {"extra_width": "D+10-8",  "tie": None,             "tie_pieces": 0},
}
ROUND_PUNCH = "D-5"
CROSS_PUNCH = "D-2.5"


def round_patch_weight(dia_cm, gsm):
    r = (dia_cm - 5) / 2.0
    return 3.14 * r * r * gsm / 10000.0


# ═══════════════════ 5. loops and belt [E] ══════════════════════════════
LOOP = {
    "cut": "2*FH + LL + SL",
    "qty": 4,
    "default_free_height_cm": 25,
    "default_LL_frac": 0.65,
    "default_SL_frac": 0.35,
    "default_belt_width_mm": 50,
    "belt_width_min_g": 25,          # below this, drop to 40 mm
    "kg_per_gram": 35,               # [E, notebook p.107]
}
BELT_WIDTH_CATALOGUE = [40, 45, 50, 60, 70, 72, 75, 80, 100]
BELT_GPM_CATALOGUE = [22, 25, 28, 30, 32, 35, 40, 42, 45, 50, 55, 60, 65]


def required_belt_gpm(swl_kg, sf, loop_qty=4):
    """[E, notebook p.107] design TARGET, not a hard limit — 45% of production
    bags sit below it, so the validator warns rather than rejects."""
    if not swl_kg or not sf:
        return None
    return swl_kg * sf / (loop_qty * LOOP["kg_per_gram"])


def loop_cut(free_height, LL, SL):
    return 2 * free_height + LL + SL


# ═══════════════════ 6. GSM, lamination, yarn ═══════════════════════════
GSM_CATALOGUE = [49, 60, 65, 70, 71, 75, 80, 85, 90, 95, 100, 103, 105, 110, 115, 120, 125, 130, 135, 140, 143, 145, 150, 155, 160, 165, 170, 175, 180, 185, 190, 195, 200, 205, 210, 220, 225, 230, 240, 245, 250, 260, 370]   # derived from the corpus, not hand-typed

LAMINATION_BANDS = [(50, 65, 15), (66, 130, 20), (131, 150, 25),
                    (151, 210, 30), (211, 240, 35)]


def lamination_coating(base_gsm):
    for lo, hi, coat in LAMINATION_BANDS:
        if lo <= base_gsm <= hi:
            return coat
    return None


SWL_BANDS = [(0, 500), (501, 750), (751, 1000), (1001, 1250), (1251, 1500),
             (1501, 1600), (1601, 1800), (1801, 2000)]

# 4-panel-baffle CORNER loop chart, bottom = body [E, rules PDF p.13].
# Used as the INTERIM floor for u_panel until the U+2 chart arrives (open O1).
GSM_CHART_CORNER = {
    5: {(0, 500): 110, (501, 750): 125, (751, 1000): 140, (1001, 1250): 160,
        (1251, 1500): 180, (1501, 1600): 190, (1601, 1800): 210, (1801, 2000): 230},
    6: {(0, 500): 120, (501, 750): 135, (751, 1000): 150, (1001, 1250): 170,
        (1251, 1500): 200, (1501, 1600): 220, (1601, 1800): 230},
}
GSM_CHART_CROSS = {
    5: {(0, 500): 120, (501, 750): 135, (751, 1000): 150, (1001, 1250): 170,
        (1251, 1500): 190, (1501, 1600): 200, (1601, 1800): 225, (1801, 2000): 240},
    6: {(0, 500): 110, (501, 750): 130, (751, 1000): 160, (1001, 1250): 180,
        (1251, 1500): 210, (1501, 1600): 225, (1601, 1800): 240},
}
BELT_CHART_CORNER = {   # (width_mm, gpm_low, gpm_high)
    5: {(0, 500): (45, 22, 25), (501, 750): (50, 25, 28), (751, 1000): (50, 30, 35),
        (1001, 1250): (50, 40, 40), (1251, 1500): (50, 45, 50),
        (1501, 1600): (50, 50, 50), (1601, 1800): (50, 55, 55), (1801, 2000): (50, 60, 60)},
    6: {(0, 500): (45, 25, 28), (501, 750): (50, 30, 32), (751, 1000): (50, 40, 40),
        (1001, 1250): (50, 45, 45), (1251, 1500): (50, 50, 50),
        (1501, 1600): (50, 55, 55), (1601, 1800): (50, 60, 60), (1801, 2000): (50, 40, 45)},
}
BELT_CHART_CROSS = {
    5: {(0, 500): (75, 35, 35), (501, 750): (75, 35, 35), (751, 1000): (80, 40, 40),
        (1001, 1250): (75, 45, 45), (1251, 1500): (75, 50, 50),
        (1501, 1600): (75, 50, 52), (1601, 1800): (75, 55, 55), (1801, 2000): (75, 60, 65)},
    6: {(0, 500): (75, 35, 35), (501, 750): (80, 40, 40), (751, 1000): (75, 45, 45),
        (1001, 1250): (75, 50, 50), (1251, 1500): (75, 55, 55),
        (1501, 1600): (75, 55, 55), (1601, 1800): (75, 60, 65), (1801, 2000): (75, 50, 50)},
}


def _band_lookup(chart, swl):
    for (lo, hi), v in chart.items():
        if lo <= swl <= hi:
            return v
    return None


def gsm_floor(swl, sf, loop_type="corner"):
    if not swl or not sf:
        return None
    sfk = 6 if int(sf) >= 6 else 5
    chart = GSM_CHART_CROSS if loop_type == "cross_corner" else GSM_CHART_CORNER
    return _band_lookup(chart.get(sfk, {}), swl)


def belt_band(swl, sf, loop_type="corner"):
    if not swl or not sf:
        return None
    sfk = 6 if int(sf) >= 6 else 5
    chart = BELT_CHART_CROSS if loop_type == "cross_corner" else BELT_CHART_CORNER
    return _band_lookup(chart.get(sfk, {}), swl)


def snap_gsm(x):
    return min(GSM_CATALOGUE, key=lambda g: abs(g - x)) if x else None


YARN_COEFF = {"u_panel": 0.45, "box": 0.45, "four_panel": 0.65,
              "four_panel_baffle": 0.70, "circular": 0.50, "pinch_corner": 0.50,
              "single_loop": 0.25, "two_loop": 0.30, "two_panel": 0.50,
              "omega": 0.50, "tunnel": 0.50, "hood": 0.45, "platten": 0.45,
              "conical": 0.65}
YARN_FLAT = {"container_liner_40ft": 300.0, "container_liner_20ft": 150.0}
YARN_OIL_ABSORPTION = 0.18       # [E, notebook p.95]


def yarn_weight(family, height_cm):
    c = YARN_COEFF.get(family)
    return c * height_cm if (c and height_cm) else None


# ═══════════════════ 7. target weight and solver [E] ════════════════════
TARGET_FACTOR = 0.99             # [E, notebook p.7] "PO bag weight minus 1%"
TOLERANCE = 0.02                 # [E, G1] +/- 2%
SOLVER_KNOBS = ["belt_gpm", "loop_cut", "body_gsm"]   # [E, G3] in this order

# ═══════════════════ 8. dust proofing, DDP [E] ══════════════════════════
DDP_GPM = 4.5
DDP_DIA_MM = 7.2
DUST_GRADES = ["NONE", "SINGLE", "DOUBLE", "TRIPLE"]   # TRIPLE = DOUBLE + FELT

JUKKI_G_PER_CM_PER_PASS = 0.5 / 6.0          # [E, notebook p.93]
JUKKI_PASS = {(0, 1200, 5): 6, (0, 1200, 6): 6, (1201, 9999, 5): 6,
              (1201, 9999, 6): 8}


def jukki_passes(swl, sf):
    if not swl or not sf:
        return 6
    sfk = 6 if int(sf) >= 6 else 5
    return 8 if (swl >= 1200 and sfk == 6) else 6


# ═══════════════════ 9. component catalogue [E] ═════════════════════════
CANONICAL = {
    "BODY PANEL": ["BODY PANEL", "BODY PANNEL", "BODY", "BODY FABRIC"],
    "SIDE PANEL": ["SIDE PANEL", "SIDE PANNEL", "SIDE FABRIC"],
    "TOP PANEL": ["TOP PANEL", "TOP PANNEL"],
    "BOTTOM PANEL": ["BOTTOM PANEL", "BOTTOM PANNEL", "BASE PANEL",
                     "BOTTOM FABRIC"],
    "FILLING SPOUT": ["FILLING SPOUT", "FS SPOUT", "F/S", "TOP SPOUT",
                      "TOP / FS", "TOP/FS", "INLET SPOUT", "FILL SPOUT", "TOP"],
    "DISCHARGE SPOUT": ["DISCHARGE SPOUT", "D/S", "D SPOUT", "DS SPOUT",
                        "BOTTOM SPOUT", "D/ SPOUT", "OUTLET SPOUT", "DS"],
    "SKIRT": ["SKIRT", "DUFFLE", "TOP/SKT", "SKIRT TOP"],
    "BAFFLE": ["BAFFLE", "BAFFLE FABRIC"],
    "CORNER LOOP": ["LOOP", "LOOPS", "CORNER LOOP", "BELT"],
    "STEVEDORE LOOP": ["STEEVE DORE", "STEEVEDORE", "STEVEDORE", "STEVEDORE LOOP"],
    "EXTRA LOOP": ["EXTRA LOOP"],
    "LOOP PROTECTOR": ["LOOP PROTECTOR"],
    "FULL BODY LOOP": ["FULL LOOP", "FULL BODY LOOP", "FULL RUNNING LOOP"],
    "IRIS TIE": ["TIE/IRIS ROPE", "IRISH TIE", "TIE/IRIS", "BRAIDED ROPE",
                 "IRIS TIE", "TIE / IRIS"],
    "FS TIE": ["FS TIE", "F/S TIE"],
    "DS TIE": ["DS TIE", "D/S TIE"],
    "TIE": ["TIE", "FS/DS TIE", "F/S & D/S TIE", "FS & DS TIE", "F/S , D/S TIE",
            "DS/FS TIE", "TIE/DS", "FS/ DS TIE", "SUPPORTING TIE",
            "TUCKING TIE", "SKIRT TIE", "FS / DS TIE"],
    "ROPE": ["ROPE", "PP ROPE"],
    "LINER": ["LINER", "PE LINER", "PP LINER"],
    "DDP": ["DDP", "DOUBLE DUST PROOF"],
    "FILLER CORD": ["FILLERCORD", "FILLER CORD", "FILLER", "DUST PROOF"],
    "FELT": ["FELT"],
    "GLUE": ["GLUE"],
    "TABBING TAPE": ["TABBING TAPE", "TABBING"],
    "B-LOCK": ["B-LOCK", "B LOCK", "BLOCK"],
    "DOC POCKET": ["DOC", "DOC POCKET", "DOCUMENT POCKET", "DOC PKT"],
    "BELLY BAND": ["BELLY BEND", "BELLY BELT", "BELLY BAND"],
    "TOP BAND": ["TOP BEND", "TOP BAND"],
    "DS FLAP": ["DS FLAP", "D/S FLAP"],
    "DS PATCH": ["DS PATCH"],
    "STITCHING": ["STITCHING", "YARN", "SEWING THREAD", "THREAD"],
    "PRINTING": ["PRINTING", "PRINT"],
    "LABEL": ["LABEL", "LEBEL"],
    "HOSE PIPE": ["HOSE PIPE", "HULE PIPE"],
}
_ALIAS = {}
for canon, alist in CANONICAL.items():
    for a in alist:
        _ALIAS.setdefault(re.sub(r"\s+", " ", a).strip().upper(), canon)

MANDATORY = {
    "u_panel": ["BODY PANEL", "SIDE PANEL", "CORNER LOOP", "STITCHING", "LABEL"],
    "box": ["BODY PANEL", "SIDE PANEL", "STITCHING", "LABEL"],
    "circular": ["BODY PANEL", "BOTTOM PANEL", "CORNER LOOP", "STITCHING", "LABEL"],
    "pinch_corner": ["BODY PANEL", "BOTTOM PANEL", "CORNER LOOP", "STITCHING", "LABEL"],
    "four_panel": ["BODY PANEL", "BOTTOM PANEL", "CORNER LOOP", "STITCHING", "LABEL"],
    "four_panel_baffle": ["BODY PANEL", "BOTTOM PANEL", "BAFFLE", "CORNER LOOP",
                          "STITCHING", "LABEL"],
    "two_panel": ["SIDE PANEL", "STITCHING", "LABEL"],
    "single_loop": ["BODY PANEL", "STITCHING", "LABEL"],
    "two_loop": ["BODY PANEL", "STITCHING", "LABEL"],
}

FORBIDDEN = {                       # phantom components per family
    "u_panel": ["BOTTOM PANEL"],    # the U-piece forms the bottom
    "box": ["BOTTOM PANEL"],
    "circular": ["SIDE PANEL"],
    "four_panel_baffle": ["SIDE PANEL"],
}


def canon_component(name):
    n = re.sub(r"\s+", " ", str(name or "")).strip().upper()
    n = n.rstrip(".:")
    if n in _ALIAS:
        return _ALIAS[n]
    for k, v in _ALIAS.items():                 # longest-first substring
        if len(k) >= 5 and k in n:
            return v
    return None


# ═══════════════════ 10. enums for the BuildSpec schema ════════════════
ENUMS = {
    "family": FAMILIES,
    "loop_type": ["corner", "cross_corner", "single", "full_running"],
    "static_type": ["A", "B", "C", "D"],
    "top_type": ["OPEN_TOP", "TOP_PANEL", "SKIRT", "TOP_FLAP", "FS_SPOUT"],
    "bottom_type": ["FLAT_BOTTOM", "DS_SPOUT"],
    "closure": ["open", "tied", "iris", "petal", "pyjama"],
    "dust_proof": DUST_GRADES,
    "liner_type": ["STANDARD", "FORM_FIT", "Q_LINER", "SUSPENDED", "SHROUD"],
    "liner_insertion": ["LOOSE", "TABBED_4", "TABBED_8", "GLUED", "HEMMED"],
    "fabric_type": ["NORMAL", "ANTISTATIC", "CONDUCTIVE", "DISSIPATIVE",
                    "EXTRA_UV", "NET", "BREATHABLE", "VENTILATED", "SANDWICH"],
    "baffle_pattern": BAFFLE["patterns"],
    "punch_type": BAFFLE["punch_types"],
    "stitch_machine": ["DR", "HR", "DDR", "VMC", "UDDR", "JUKKI"],
    "stitch_spec": ["OVERLOCK_CHAIN", "DOUBLE_CHAIN", "DOUBLE_NEEDLE"],
    "fold_spec": ["OUT_FOLD", "J_FOLD"],
    "fold_mode": ["SINGLE", "DOUBLE"],
    "body_gsm": GSM_CATALOGUE,
    "belt_width_mm": BELT_WIDTH_CATALOGUE,
    "belt_gpm": BELT_GPM_CATALOGUE,
    "loop_qty": [1, 2, 4],
    "yarn_white_denier": [2200, 3000, 3200, 3500],
    "yarn_blue_denier": [3600, 8500],
}

RULE_VERSION = "1.1"
