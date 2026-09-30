"""Stage 1 — extraction (adapter A).  enquiry text -> OrderSpec.

With a model `client`: grammar-constrained call, then an evidence check drops any
field whose value is not a substring of the enquiry (plan §4.1 hallucination
guard). Without a client: a compact regex fallback (a trimmed port of
06_adapter_a.verify_parse) so the pipeline runs with no GPU.
"""
from __future__ import annotations
import json
import re

from .contracts import OrderSpec, Field

SYSTEM_A = (
    "You are an extraction engine for Anjani Interweave FIBC enquiries. Read the "
    "enquiry and return an OrderSpec JSON containing ONLY what the customer "
    "actually stated. Every field you cannot find in the text must be returned "
    "with state 'not_specified' and value null. Never infer, never default, "
    "never fill a gap from experience. Convert units to cm, kg and grams. "
    "Output JSON only."
)


# ── regex fallback ────────────────────────────────────────────────────
def _regex_order_spec(text: str) -> dict:
    s = re.sub(r"[ \t]+", " ", text)
    up = s.upper()
    f: dict[str, tuple] = {}

    def put(k, v, ev):
        f[k] = (v, ev)

    m = re.search(r"(\d+(?:\.\d+)?)\s*[xX*]\s*(\d+(?:\.\d+)?)\s*[xX*]\s*(\d+(?:\.\d+)?)", s)
    if m:
        for k, i in (("ext_L_cm", 1), ("ext_W_cm", 2), ("ext_H_cm", 3)):
            put(k, float(m.group(i)), m.group(0))
    m = re.search(r"(?:INTERNAL|\bINT\b|\bID\b)\s*:?\s*(\d+(?:\.\d+)?)\s*[X*]\s*"
                  r"(\d+(?:\.\d+)?)\s*[X*]\s*(\d+(?:\.\d+)?)", up)
    if m:
        for k, i in (("int_L_cm", 1), ("int_W_cm", 2), ("int_H_cm", 3)):
            put(k, float(m.group(i)), m.group(0))
    m = re.search(r"(?:SWL|SAFE WORKING LOAD|LOADING CAPACITY)[^0-9]{0,16}"
                  r"(\d+(?:\.\d+)?)\s*(KGS?|TON|MT)?", up)
    if m:
        v = float(m.group(1)) * (1000 if (m.group(2) or "").startswith(("TON", "MT")) else 1)
        put("swl_kg", v, m.group(0))
    m = re.search(r"(?:SF|SAFETY FACTOR)[^0-9]{0,16}0?(\d)\s*(?::|\.|IS TO )\s*0?(\d)", up)
    if m:
        put("sf", f"{m.group(1)}:{m.group(2)}", m.group(0))
    m = re.search(r"WEIGHT[^0-9]{0,10}(\d+(?:\.\d+)?)\s*(KG|GM|GRAM|G\b)", up)
    if m:
        v = float(m.group(1)) * (1000 if m.group(2).startswith("KG") else 1)
        put("req_weight_g", v, m.group(0))
    m = re.search(r"(\d+)\s*LOOP", up)
    if m:
        put("loop_qty", float(m.group(1)), m.group(0))
    m = re.search(r"FREE HEIGHT\s*(\d+(?:\.\d+)?)", up)
    if m:
        put("loop_free_height_cm", float(m.group(1)), m.group(0))
    for tag, key in (("LL", "loop_LL_cm"), ("SL", "loop_SL_cm")):
        mm = re.search(rf"\b{tag}\s*(\d+(?:\.\d+)?)", up)
        if mm:
            put(key, float(mm.group(1)), mm.group(0))
    m = (re.search(r"(?:BELT|LIFT STRAPS?|LOOP)[^0-9]{0,12}(\d+(?:\.\d+)?)\s*MM", up)
         or re.search(r"(\d+(?:\.\d+)?)\s*MM\s*(?:PP\s*)?(?:BELT|WEBBING|STRAP)", up))
    if m:
        put("belt_width_mm", float(m.group(1)), m.group(0))
    m = re.search(r"(?:BAG TYPE|CONSTRUCTION|PRODUCTION LINE|TYPE)\s*[:\-]\s*"
                  r"([A-Z0-9 /+\-]{3,40})", up)
    if m:
        put("stated_bag_type_raw", m.group(1).strip(), m.group(0))
    if re.search(r"LINER REQUIRED|LINER\s+\d+\s*MICRON", up):
        put("has_liner", True, "liner")
    if "DOCUMENT POCKET" in up or "DOCUMENT POUCH" in up or "DOC PKT" in up:
        put("has_doc_pocket", True, "doc pocket")
    if re.search(r"PRINTING REQUIRED|PRINTING\s+\d\s*SIDE", up):
        put("has_printing", True, "printing")

    out = {"raw_text": text}
    for k, (v, ev) in f.items():
        out[k] = {"value": v, "state": "provided", "evidence": ev}
    return out


# ── evidence check ────────────────────────────────────────────────────
def _supported(value, text: str) -> bool:
    if value is None or isinstance(value, bool):
        return True
    t = text.lower()
    if isinstance(value, (int, float)):
        v = float(value)
        for c in {v, v / 1000, v * 1000, round(v)}:
            s = str(int(c)) if float(c).is_integer() else f"{c:g}"
            if re.search(rf"(?<!\d){re.escape(s)}(?!\d)", t):
                return True
        return False
    s = str(value).strip().lower()
    return (not s) or s in t or all(w in t for w in re.split(r"[\s/_+-]+", s) if len(w) > 2)


def extract(text: str, client=None) -> OrderSpec:
    if client is not None:
        raw = client.complete("a", SYSTEM_A, text)
        try:
            d = json.loads(raw)
        except json.JSONDecodeError:
            d = _regex_order_spec(text)
        d["raw_text"] = text
        # hallucination guard: demote unsupported "provided" fields
        for k, fv in list(d.items()):
            if isinstance(fv, dict) and fv.get("state") == "provided":
                if not _supported(fv.get("value"), text):
                    d[k] = {"value": None, "state": "not_specified",
                            "evidence": None, "_dropped": fv.get("value")}
    else:
        d = _regex_order_spec(text)
    return OrderSpec.from_dict(d)
