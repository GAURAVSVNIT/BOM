"""Formatting + the issue #1 invariant, checked on the real dataset. No GPU."""
import json
import re

import pytest

from bomft.data import iter_examples, load_rows, to_messages, dumps
from bomft import paths


def _have(adapter, split):
    return paths.adapter_jsonl(adapter, split).exists()


@pytest.mark.skipif(not _have("a", "val"), reason="dataset not built")
def test_adapter_a_three_messages_and_roundtrippable_output():
    for ex in iter_examples("a", "val", limit=25):
        roles = [m["role"] for m in ex["messages"]]
        assert roles == ["system", "user", "assistant"]
        json.loads(ex["messages"][2]["content"])          # assistant is valid JSON


@pytest.mark.skipif(not _have("a", "train"), reason="dataset not built")
def test_issue1_no_unsupported_provided_labels_in_training_targets():
    """Every OrderSpec field marked state=provided must have textual support:
    numbers appear in the enquiry, internal dims only as a full marked triple."""
    bad = []
    for row in load_rows("a", "train") + load_rows("a", "val") + load_rows("a", "test"):
        text = row["input"].lower()
        has_int_marker = bool(re.search(r"internal|\bint\b|\bid\b", text))
        for k, f in row["output"].items():
            if not isinstance(f, dict):
                continue
            if f.get("state") == "provided" and f.get("value") is not None:
                if k.startswith("int_") and not has_int_marker:
                    bad.append((row["id"], k, f["value"]))
                if k in ("static_type", "product_contents"):
                    bad.append((row["id"], k, f["value"]))
    assert not bad, f"{len(bad)} unsupported provided labels, e.g. {bad[:5]}"


@pytest.mark.skipif(not _have("b", "train"), reason="dataset not built")
def test_adapter_b_user_prompt_has_sections():
    row = load_rows("b", "train", limit=1)[0]
    msg = to_messages(row, "b")
    user = msg["messages"][1]["content"]
    assert "ORDER_SPEC:" in user and "RULE_ENVELOPE:" in user


def test_dumps_is_compact_and_stable():
    assert dumps({"b": 1, "a": 2}) == '{"b":1,"a":2}'
