"""The guided-json schemas build from the live rule book and pin the vocab."""
import pytest

from bomft.schema import order_spec_schema, build_spec_schema, guided_json, _rules
from bomft import paths


def test_order_spec_schema_shape():
    s = order_spec_schema()
    assert s["type"] == "object" and s["additionalProperties"] is False
    f = s["properties"]["ext_L_cm"]
    assert set(f["required"]) == {"value", "state"}
    assert f["properties"]["value"]["type"] == ["number", "null"]


@pytest.mark.skipif(not paths.gold_jsonl("build_spec").exists(), reason="dataset not built")
def test_build_spec_schema_pins_enums_from_rules():
    R = _rules()
    s = build_spec_schema()
    fam = s["properties"]["family"]
    vals = fam["anyOf"][0]["enum"]
    assert set(vals) == set(R.ENUMS["family"])
    gsm = s["properties"]["body_gsm"]["anyOf"][0]["enum"]
    assert gsm == list(R.GSM_CATALOGUE)


@pytest.mark.skipif(not paths.gold_jsonl("build_spec").exists(), reason="dataset not built")
def test_build_output_allows_bare_and_wrapped():
    s = guided_json("b")
    assert "anyOf" in s and len(s["anyOf"]) == 2
    wrapped = s["anyOf"][1]
    assert "build_spec" in wrapped["properties"]
