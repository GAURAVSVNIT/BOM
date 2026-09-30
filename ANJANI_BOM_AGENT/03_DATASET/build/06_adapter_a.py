# -*- coding: utf-8 -*-
"""
06_adapter_a.py — the EXTRACTION dataset.  enquiry text -> OrderSpec

Adapter A must read only what the customer said and mark everything else
not_specified. Its training rows therefore need realistic enquiry TEXT, which
the corpus does not contain — the sheets hold the engineer's transcription of
the enquiry, not the enquiry itself.

So the text is synthesised FROM OrderSpec_gold, and every row is round-trip
verified: an INDEPENDENT parser (verify.py logic below, sharing no code with the
generator) re-reads the generated text and must recover the same field values.
Any mismatch is DISCARDED, never repaired.

Field dropout follows the rates measured on the corpus, so a synthetic enquiry
is as incomplete as a real one.
"""
import os, sys, re, json, random, collections, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rules as R

from _bompaths import ROOT, OUT, GOLD  # portable paths; see _bompaths.py
DEST = os.path.join(OUT, "adapter_a")
os.makedirs(DEST, exist_ok=True)
random.seed(20260826)

order = [json.loads(l) for l in open(os.path.join(GOLD, "order_spec.jsonl"), encoding="utf-8")]
split = json.load(open(os.path.join(OUT, "split.json"), encoding="utf-8"))
which = {i: s for s, ids in split.items() for i in ids}

# fields the extractor is graded on
FIELDS = ["customer", "ext_L_cm", "ext_W_cm", "ext_H_cm", "int_L_cm", "int_W_cm",
          "int_H_cm", "swl_kg", "sf", "req_weight_g", "quoted_weight_g",
          "stated_bag_type_raw", "fabric_colour", "loop_qty",
          "loop_free_height_cm", "loop_LL_cm", "loop_SL_cm", "belt_width_mm",
          "loop_colour", "top_type", "fs_dia_cm", "fs_height_cm", "fs_closure",
          "bottom_type", "ds_dia_cm", "ds_height_cm", "ds_closure",
          "has_liner", "liner_micron", "has_doc_pocket", "has_printing",
          "printing_sides", "packing", "order_qty", "product_contents",
          "static_type"]

# issue #1: fields no generator ever renders into text. They used to slip into
# `vis` on a lucky dropout roll and then get stamped state="provided" in the
# target — teaching the extractor to assert a value the enquiry never contained,
# which is exactly the hallucination the firewall design exists to prevent.
# `static_type` / `product_contents` are never emitted; internal dims are only
# ever emitted as a COMPLETE triple, and only by the whatsapp/email/phone
# generators (handled in the main loop + STYLE_CANNOT below).
NEVER_VISIBLE = {"static_type", "product_contents"}

# dropout rates measured on the corpus (§1.15 of the plan)
DROP = {"packing": 0.17, "has_printing": 0.43, "has_doc_pocket": 0.45,
        "has_liner": 0.78, "req_weight_g": 0.09, "swl_kg": 0.05,
        "order_qty": 0.40, "loop_LL_cm": 0.40, "loop_SL_cm": 0.45,
        "loop_colour": 0.35, "fabric_colour": 0.25, "customer": 0.20,
        "int_L_cm": 0.30, "int_W_cm": 0.30, "int_H_cm": 0.30,
        "belt_width_mm": 0.30, "printing_sides": 0.55, "liner_micron": 0.55}

# noise seen verbatim in the corpus
TYPOS = [("PANEL", "PANNEL"), ("CLOSURE", "CLOUSER"), ("CIRCULAR", "CIRCULER"),
         ("BAG", "BAG"), ("TUBULAR", "TUBELAR"), ("BAFFLE", "BAFFEL"),
         ("DISCHARGE", "DISCHRGE"), ("PANEL", "APNNEL")]
KG_FORMS = ["{v} KG", "{v}kg", "{v} KGS", "{v} Kg"]
G_FORMS = ["{v} gm", "{v} GRAM", "{v}g", "{v} gms"]
SF_FORMS = ["{a}:{b}", "{a}:0{b}", "0{a}:0{b}", "{a} is to {b}", "{a}:{b}/UN"]


def V(o, k):
    f = o.get(k)
    return f.get("value") if isinstance(f, dict) else None


def fmt_num(x):
    if x is None:
        return None
    return str(int(x)) if float(x) == int(float(x)) else str(round(float(x), 2))


# ══════════════════ enquiry generator ═══════════════════════════════════
def build_visible(o, rng):
    """Decide which fields survive into the enquiry text."""
    vis = {}
    for k in FIELDS:
        if k in NEVER_VISIBLE:
            continue
        v = V(o, k)
        if v is None:
            continue
        if rng.random() < DROP.get(k, 0.0):
            continue
        vis[k] = v
    # a real enquiry always carries at least a size
    for k in ("ext_L_cm", "ext_W_cm", "ext_H_cm"):
        if V(o, k) is not None:
            vis[k] = V(o, k)
    # internal dims are only ever rendered as a complete L x W x H triple; a
    # partial survivor would be an unsupported "provided" label, so drop it.
    if not all(f"int_{a}_cm" in vis for a in ("L", "W", "H")):
        for a in ("L", "W", "H"):
            vis.pop(f"int_{a}_cm", None)
    return vis


def _size(vis, rng, tag="ext"):
    L, W, H = vis.get(f"{tag}_L_cm"), vis.get(f"{tag}_W_cm"), vis.get(f"{tag}_H_cm")
    if not (L and W and H):
        return None
    sep = rng.choice(["x", "X", " x ", "*", " X "])
    return f"{fmt_num(L)}{sep}{fmt_num(W)}{sep}{fmt_num(H)}"


def gen_whatsapp(vis, rng, hinglish=False):
    L = []
    hi = hinglish
    s = _size(vis, rng)
    if s:
        L.append(rng.choice([f"Bag size {s} cm", f"size : {s} cm",
                             f"{s} cm bag", f"Bag size : {s}"]))
    si = _size(vis, rng, "int")
    if si:
        L.append(f"internal {si} cm")
    if "stated_bag_type_raw" in vis:
        L.append(rng.choice(["Bag type : ", "type - ", "construction : "]) +
                 str(vis["stated_bag_type_raw"]))
    if "swl_kg" in vis:
        L.append(rng.choice(["SWL ", "swl - ", "loading capacity "]) +
                 rng.choice(KG_FORMS).format(v=fmt_num(vis["swl_kg"])))
    if "sf" in vis:
        a, b = str(vis["sf"]).split(":")
        L.append(rng.choice(["SF ", "sf : ", "safety factor "]) +
                 rng.choice(SF_FORMS).format(a=a, b=b))
    if "req_weight_g" in vis or "quoted_weight_g" in vis:
        w = vis.get("req_weight_g") or vis.get("quoted_weight_g")
        if rng.random() < 0.5:
            L.append("weight " + rng.choice(KG_FORMS).format(v=round(w / 1000.0, 3)))
        else:
            L.append("weight " + rng.choice(G_FORMS).format(v=fmt_num(w)))
    if "fabric_colour" in vis:
        L.append(("colour " if rng.random() < .5 else "color ") + str(vis["fabric_colour"]).lower())
    if "top_type" in vis:
        tt = {"OPEN_TOP": "open top", "SKIRT": "skirt top", "TOP_PANEL": "closed top",
              "TOP_FLAP": "top flap", "FS_SPOUT": "top spout"}.get(vis["top_type"], "")
        if "fs_dia_cm" in vis and "fs_height_cm" in vis:
            tt += f" {fmt_num(vis['fs_dia_cm'])}x{fmt_num(vis['fs_height_cm'])} cm"
        if "fs_closure" in vis and vis["fs_closure"] != "open":
            tt += f" with {vis['fs_closure']} closure"
        if tt.strip():
            L.append(tt.strip())
    if "bottom_type" in vis:
        bt = {"FLAT_BOTTOM": "flat bottom", "DS_SPOUT": "bottom spout"}.get(vis["bottom_type"], "")
        if "ds_dia_cm" in vis and "ds_height_cm" in vis:
            bt += f" {fmt_num(vis['ds_dia_cm'])}x{fmt_num(vis['ds_height_cm'])} cm"
        if "ds_closure" in vis and vis["ds_closure"] != "open":
            bt += f" with {vis['ds_closure']} closer"
        if bt.strip():
            L.append(bt.strip())
    lp = []
    if "loop_qty" in vis:
        lp.append(f"{int(vis['loop_qty'])} loop")
    if "loop_free_height_cm" in vis:
        lp.append(f"free height {fmt_num(vis['loop_free_height_cm'])} cm")
    if "loop_LL_cm" in vis:
        lp.append(f"LL {fmt_num(vis['loop_LL_cm'])} cm")
    if "loop_SL_cm" in vis:
        lp.append(f"SL {fmt_num(vis['loop_SL_cm'])} cm")
    if "belt_width_mm" in vis:
        lp.append(f"belt {fmt_num(vis['belt_width_mm'])} mm")
    if "loop_colour" in vis:
        lp.append(str(vis["loop_colour"]).lower() + " belt")
    if lp:
        L.append("loop : " + ", ".join(lp))
    if vis.get("has_liner"):
        t = "liner required"
        if "liner_micron" in vis:
            t += f" {fmt_num(vis['liner_micron'])} micron"
        L.append(t)
    if vis.get("has_doc_pocket"):
        L.append("document pocket required")
    if vis.get("has_printing"):
        t = "printing required"
        if "printing_sides" in vis:
            t += f" {int(vis['printing_sides'])} side"
        L.append(t)
    if "packing" in vis:
        L.append("packing " + str(vis["packing"]))
    if "order_qty" in vis:
        L.append(f"qty {fmt_num(vis['order_qty'])} pcs")
    if "customer" in vis:
        L.insert(0, f"{vis['customer']} enquiry")
    if hi:
        L.append(rng.choice(["rate bata dijiye", "please quote karo",
                             "jaldi bhej dena", "confirm kar dena"]))
    return "\n".join(L)


def gen_email(vis, rng):
    body = gen_whatsapp(vis, rng)
    head = rng.choice(["Dear Sir,\n\nPlease quote for the following FIBC:",
                       "Hello,\n\nKindly send your best offer for:",
                       "Dear Team,\n\nRequirement as below:"])
    tail = rng.choice(["\n\nAwaiting your revert.\nRegards",
                       "\n\nPlease confirm availability.\nThanks & Regards",
                       "\n\nBest regards"])
    return head + "\n" + body + tail


def gen_tds(vis, rng):
    rows = []
    if "customer" in vis:
        rows.append(f"CUSTOMER : {vis['customer']}")
    rows.append("SPECIFICATION DRAWING SHEET")
    s = _size(vis, rng)
    if s:
        rows.append(f"SIZE: {s} cms.")
    if "swl_kg" in vis:
        rows.append(f"SAFE WORKING LOAD: {fmt_num(vis['swl_kg'])} KGS.")
    if "sf" in vis:
        rows.append(f"SAFETY FACTOR : {vis['sf']}")
    if "stated_bag_type_raw" in vis:
        rows.append(f"PRODUCTION LINE: {vis['stated_bag_type_raw']}")
    if "fabric_colour" in vis:
        rows.append(f"FABRIC: PP {vis['fabric_colour']}")
    n = 1
    if "belt_width_mm" in vis:
        rows.append(f"{n}  LIFT STRAPS   {fmt_num(vis['belt_width_mm'])} mm PP")
        n += 1
    if "fs_dia_cm" in vis:
        rows.append(f"{n}  TOP SPOUT     {fmt_num(vis['fs_dia_cm'])} cm Dia x "
                    f"{fmt_num(vis.get('fs_height_cm') or 50)} cm long")
        n += 1
    if "ds_dia_cm" in vis:
        rows.append(f"{n}  BOTTOM SPOUT  {fmt_num(vis['ds_dia_cm'])} cm Dia x "
                    f"{fmt_num(vis.get('ds_height_cm') or 50)} cm long")
        n += 1
    if vis.get("has_doc_pocket"):
        rows.append(f"{n}  DOCUMENT POUCH  one zip lock"); n += 1
    if vis.get("has_printing"):
        rows.append(f"{n}  PRINTING  {int(vis.get('printing_sides') or 1)} side"); n += 1
    if "packing" in vis:
        rows.append(f"PACKAGING  {vis['packing']}")
    if "req_weight_g" in vis or "quoted_weight_g" in vis:
        w = vis.get("req_weight_g") or vis.get("quoted_weight_g")
        rows.append(f"BAG WEIGHT: {round(w/1000.0,3)} KG")
    return "\n".join(rows)


def gen_phone(vis, rng):
    t = gen_whatsapp(vis, rng)
    return "call notes -\n" + t.replace("\n", " ; ")


STYLES = [("whatsapp_en", lambda v, r: gen_whatsapp(v, r, False)),
          ("whatsapp_hinglish", lambda v, r: gen_whatsapp(v, r, True)),
          ("email_formal", gen_email),
          ("tds_table", gen_tds),
          ("phone_notes", gen_phone)]

# A style can only be graded on fields it is structurally able to express.
# A printed technical data sheet, for instance, carries no LL/SL loop lengths
# and no free height — grading it on those would discard sound rows.
STYLE_CANNOT = {
    # gen_tds() renders only the EXTERNAL size, never an internal triple, so
    # int_* here would be an unsupported "provided" label (issue #1).
    "tds_table": {"loop_qty", "loop_free_height_cm", "loop_LL_cm", "loop_SL_cm",
                  "loop_colour", "has_liner", "liner_micron", "top_type",
                  "bottom_type", "fs_closure", "ds_closure", "order_qty",
                  "int_L_cm", "int_W_cm", "int_H_cm"},
    "whatsapp_en": set(), "whatsapp_hinglish": set(),
    "email_formal": set(), "phone_notes": set(),
}


def add_noise(txt, rng):
    if rng.random() < 0.35:
        a, b = rng.choice(TYPOS)
        txt = re.sub(a, b, txt, count=1, flags=re.I)
    if rng.random() < 0.15:
        txt = txt.replace(" cm", "cm", 1)
    if rng.random() < 0.10:
        txt = txt.upper()
    return txt


# ══════════════════ INDEPENDENT verifier ════════════════════════════════
# Written against the enquiry TEXT only. Shares no code with the generator.
def verify_parse(txt):
    s = re.sub(r"[ \t]+", " ", txt)
    up = s.upper()
    out = {}
    m = re.search(r"(\d+(?:\.\d+)?)\s*[xX*]\s*(\d+(?:\.\d+)?)\s*[xX*]\s*(\d+(?:\.\d+)?)", s)
    if m:
        out["ext_L_cm"], out["ext_W_cm"], out["ext_H_cm"] = [float(m.group(i)) for i in (1, 2, 3)]
    # internal triple is always marker-anchored ("internal 95x95x120 cm")
    m = re.search(r"(?:INTERNAL|\bINT\b|\bID\b)\s*:?\s*(\d+(?:\.\d+)?)\s*[X*]\s*"
                  r"(\d+(?:\.\d+)?)\s*[X*]\s*(\d+(?:\.\d+)?)", up)
    if m:
        out["int_L_cm"], out["int_W_cm"], out["int_H_cm"] = [float(m.group(i)) for i in (1, 2, 3)]
    m = re.search(r"(?:SWL|SAFE WORKING LOAD|LOADING CAPACITY)[^0-9]{0,16}"
                  r"(\d+(?:\.\d+)?)\s*(KGS?|TON)?", up)
    if m:
        v = float(m.group(1))
        out["swl_kg"] = v * 1000 if (m.group(2) or "").startswith("TON") else v
    # leading zeros ("05:01"), decimal form ("5.1"), and the "/UN" suffix all occur
    m = re.search(r"(?:SF|SAFETY FACTOR)[^0-9]{0,16}0?(\d)\s*(?::|\.|IS TO )\s*0?(\d)", up)
    if m:
        out["sf"] = f"{m.group(1)}:{m.group(2)}"
    m = re.search(r"WEIGHT[^0-9]{0,10}(\d+(?:\.\d+)?)\s*(KG|GM|GRAM|G\b)", up)
    if m:
        v = float(m.group(1))
        out["weight_g"] = v * 1000 if m.group(2).startswith("KG") else v
    m = re.search(r"(\d+)\s*LOOP", up)
    if m:
        out["loop_qty"] = float(m.group(1))
    m = re.search(r"FREE HEIGHT\s*(\d+(?:\.\d+)?)", up)
    if m:
        out["loop_free_height_cm"] = float(m.group(1))
    m = re.search(r"\bLL\s*(\d+(?:\.\d+)?)", up)
    if m:
        out["loop_LL_cm"] = float(m.group(1))
    m = re.search(r"\bSL\s*(\d+(?:\.\d+)?)", up)
    if m:
        out["loop_SL_cm"] = float(m.group(1))
    m = re.search(r"(?:BELT|LIFT STRAPS?)[^0-9]{0,12}(\d+(?:\.\d+)?)\s*MM", up)
    if m:
        out["belt_width_mm"] = float(m.group(1))
    # "LINER" also appears inside bag-type strings ("CONTAINER LINER BAG",
    # "4 PANNEL BAG WITH FLANGE LINER"), so match the requirement phrase, not
    # the bare word, or every container bag reads as liner-required.
    out["has_liner"] = bool(re.search(r"LINER REQUIRED|LINER\s+\d+\s*MICRON", up))
    out["has_doc_pocket"] = ("DOCUMENT POCKET" in up or "DOCUMENT POUCH" in up)
    out["has_printing"] = bool(re.search(r"PRINTING REQUIRED|PRINTING\s+\d\s*SIDE|"
                                         r"\bPRINTING\s+\d", up))
    return out


CHECK = ["ext_L_cm", "ext_W_cm", "ext_H_cm", "int_L_cm", "int_W_cm", "int_H_cm",
         "swl_kg", "sf", "loop_qty", "loop_free_height_cm", "loop_LL_cm",
         "loop_SL_cm", "belt_width_mm"]


def round_trip_ok(vis, txt):
    got = verify_parse(txt)
    for k in CHECK:
        if k in vis:
            g = got.get(k)
            if g is None:
                return False, f"lost {k}"
            if isinstance(vis[k], (int, float)) and abs(float(g) - float(vis[k])) > 0.01:
                return False, f"garbled {k}: {vis[k]} -> {g}"
            if isinstance(vis[k], str) and str(g) != str(vis[k]):
                return False, f"garbled {k}"
    for b in ("has_liner", "has_doc_pocket", "has_printing"):
        if bool(vis.get(b)) != bool(got.get(b)):
            return False, f"boolean flip {b}"
    if "req_weight_g" in vis or "quoted_weight_g" in vis:
        want = vis.get("req_weight_g") or vis.get("quoted_weight_g")
        g = got.get("weight_g")
        if g is None or abs(g - want) / want > 0.02:
            return False, "weight lost or garbled"
    return True, None


# ══════════════════ target OrderSpec (masked to what is visible) ════════
def target_spec(o, vis):
    t = {"source_type": "enquiry_text"}
    for k in FIELDS:
        v = V(o, k)
        if k in vis:
            t[k] = {"value": v, "state": "provided"}
        else:
            t[k] = {"value": None, "state": "not_specified"}
    return t


SYSTEM_A = (
    "You are an extraction engine for Anjani Interweave FIBC enquiries. "
    "Read the enquiry and return an OrderSpec JSON containing ONLY what the "
    "customer actually stated. Every field you cannot find in the text must be "
    "returned with state 'not_specified' and value null. Never infer, never "
    "default, never fill a gap from experience. Convert units to cm, kg and "
    "grams. Output JSON only."
)

rows, rejected, agg = [], collections.Counter(), collections.Counter()
for o in order:
    sp = which.get(o["_id"])
    if sp is None:
        continue
    for style_name, fn in STYLES:
        rng = random.Random(hashlib.sha1((o["_id"] + style_name).encode()).hexdigest()[:8])
        vis = build_visible(o, rng)
        vis = {k: v for k, v in vis.items() if k not in STYLE_CANNOT[style_name]}
        if len([k for k in vis if k.startswith("ext_")]) < 3:
            agg["skip_no_size"] += 1
            continue
        txt = add_noise(fn(vis, rng), rng)
        ok, why = round_trip_ok(vis, txt)
        if not ok:
            rejected[why.split(":")[0]] += 1
            agg["discarded"] += 1
            continue
        rows.append({
            "split": sp, "adapter": "A", "style": style_name,
            "id": o["_id"] + "_" + style_name,
            "fingerprint": o["_fingerprint"],
            "system": SYSTEM_A,
            "input": txt,
            "output": target_spec(o, vis),
            "meta": {"source": o["_source"], "synthetic": True,
                     "round_trip_verified": True,
                     "n_fields_visible": len(vis)},
        })
        agg["kept"] += 1
        agg["kept_" + sp] += 1

print("=" * 78)
print("ADAPTER A — extraction dataset")
print("=" * 78)
print(f"  candidates          {agg['kept']+agg['discarded']}")
print(f"  kept (verified)     {agg['kept']}")
print(f"  discarded           {agg['discarded']}"
      f"  ({100*agg['discarded']/max(agg['kept']+agg['discarded'],1):.1f}%)")
print("  discard reasons:")
for k, v in rejected.most_common(10):
    print(f"     {v:5d}  {k}")
print("  by split:", {s: agg['kept_' + s] for s in ('train', 'val', 'test') if 'kept_' + s in agg})
print("  by style:", dict(collections.Counter(r['style'] for r in rows)))

# ── hard negatives — the cases a regex gets wrong ───────────────────────
HARD = [
 ("U+2 panel bag 90x90x120 cm, SWL 1000 kg, SF 5:1, top spout 40x50, bottom irish 35x50",
  {"ext_L_cm": 90, "ext_W_cm": 90, "ext_H_cm": 120, "swl_kg": 1000, "sf": "5:1",
   "fs_dia_cm": 40, "fs_height_cm": 50, "ds_dia_cm": 35, "ds_height_cm": 50,
   "ds_closure": "iris"},
  "two size pairs after the bag size; the spout sizes must not overwrite it"),
 ("Bag 95x95x110 cm external, 91x91x106 internal. SWL 1250. 5:1",
  {"ext_L_cm": 95, "ext_W_cm": 95, "ext_H_cm": 110, "int_L_cm": 91,
   "int_W_cm": 91, "int_H_cm": 106, "swl_kg": 1250, "sf": "5:1"},
  "two size triples, one labelled internal"),
 ("90x90x100 open top flat bottom WITHOUT liner, bina printing ke, 1000 kg 5:1",
  {"ext_L_cm": 90, "ext_W_cm": 90, "ext_H_cm": 100, "swl_kg": 1000, "sf": "5:1",
   "has_liner": False, "has_printing": False, "top_type": "OPEN_TOP",
   "bottom_type": "FLAT_BOTTOM"},
  "negation in English and Hinglish"),
 ("SIZE: 103 X 103 X 200 cms.  SAFE WORKING LOAD: 1500 KGS.  SAFETY FACTOR : 5:1\n"
  "FABRIC: 220 gr/m2 PP WHITE UNCOATED\nLIFT STRAPS 3\" PP white, 30 cm lenght loop.\n"
  "BOTTOM SPOUT  80 cm Dia x 60 cm long",
  {"ext_L_cm": 103, "ext_W_cm": 103, "ext_H_cm": 200, "swl_kg": 1500, "sf": "5:1",
   "belt_width_mm": 76.2, "loop_free_height_cm": 30, "ds_dia_cm": 80, "ds_height_cm": 60},
  "TDS style: imperial inches, gr/m2 not GSM, 'Dia' keyword, typo 'lenght'"),
 ("jumbo bag chahiye 100x100x120, swl 1 ton, 6:01/UN, 4 corner loop 50mm belt",
  {"ext_L_cm": 100, "ext_W_cm": 100, "ext_H_cm": 120, "swl_kg": 1000,
   "sf": "6:1", "loop_qty": 4, "belt_width_mm": 50},
  "'1 ton' and the 6:01/UN safety-factor spelling"),
 ("U PANNEL BAG 85X85X85 CM GSM 150 SWL 1000KG SF 5.1 WEIGHT 720 G",
  {"ext_L_cm": 85, "ext_W_cm": 85, "ext_H_cm": 85, "swl_kg": 1000, "sf": "5:1",
   "req_weight_g": 720},
  "the reference enquiry: SF written 5.1, weight in g, PANNEL spelling"),
 ("Q bag 105x105x120 cm ID, 4 panel baffle, cross corner 75mm, 1000kg 5:1",
  {"int_L_cm": 105, "int_W_cm": 105, "int_H_cm": 120, "swl_kg": 1000,
   "sf": "5:1", "belt_width_mm": 75},
  "size given as INTERNAL only; Q bag = 4-panel baffle"),
 ("circular bag 90 x 90 x 114, cross corner loop, skirt 80 cm, iris closer bottom 40x50",
  {"ext_L_cm": 90, "ext_W_cm": 90, "ext_H_cm": 114, "top_type": "SKIRT",
   "ds_dia_cm": 40, "ds_height_cm": 50, "ds_closure": "iris"},
  "no SWL at all; skirt height must not be read as a spout size"),
]
hard_rows = []
for i, (txt, fields, why) in enumerate(HARD):
    t = {"source_type": "enquiry_text"}
    for k in FIELDS:
        t[k] = {"value": fields.get(k), "state": "provided" if k in fields
                else "not_specified"}
    hard_rows.append({"split": "train", "adapter": "A", "style": "hard_negative",
                      "id": f"hardneg_{i:03d}", "fingerprint": f"HN{i:03d}",
                      "system": SYSTEM_A, "input": txt, "output": t,
                      "meta": {"synthetic": False, "hand_written": True,
                               "why": why}})

by_split = collections.defaultdict(list)
for r in rows:
    by_split[r["split"]].append(r)
by_split["train"].extend(hard_rows)

for s in ("train", "val", "test"):
    with open(os.path.join(DEST, s + ".jsonl"), "w", encoding="utf-8") as f:
        for r in by_split[s]:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
with open(os.path.join(DEST, "hard_negatives.jsonl"), "w", encoding="utf-8") as f:
    for r in hard_rows:
        f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")

print(f"\n  hard negatives      {len(hard_rows)}  (hand written, added to train)")
print(f"  FINAL   train {len(by_split['train'])}  val {len(by_split['val'])}"
      f"  test {len(by_split['test'])}")
print(f"  wrote {DEST}")
