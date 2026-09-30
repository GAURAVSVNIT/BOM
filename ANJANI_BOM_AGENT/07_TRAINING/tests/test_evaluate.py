"""Metric functions on synthetic predictions — deterministic, no model."""
from bomft.evaluate import (evidence_supported, score_adapter_a, score_adapter_b,
                            check_gates, GATES_A)


def test_evidence_supported_numbers_and_units():
    assert evidence_supported(90, "bag 90x90x120 cm")
    assert evidence_supported(2500, "weight 2.5 kg")           # g <-> kg
    assert not evidence_supported(77, "bag 90x90x120 cm")
    assert evidence_supported("SKIRT", "duffle / skirt top")   # token match


def test_adapter_a_scoring_flags_hallucination():
    """Operational hallucination = gold not_specified but model asserts a value."""
    gold = [{
        "id": "x", "input": "bag 90x90x120 cm, SWL 1000",
        "output": {
            "ext_L_cm": {"value": 90, "state": "provided"},
            "swl_kg": {"value": 1000, "state": "provided"},
            "int_W_cm": {"value": None, "state": "not_specified"},
            "has_liner": {"value": None, "state": "not_specified"},
            "sf": {"value": None, "state": "not_specified"},
        },
    }]
    preds = {"x": {"output": {
        "ext_L_cm": {"value": 90, "state": "provided"},
        "swl_kg": {"value": 1000, "state": "provided"},
        "int_W_cm": {"value": 84, "state": "provided"},      # hallucinated
        "has_liner": {"value": True, "state": "provided"},   # hallucinated
        "sf": {"value": None, "state": "not_specified"},     # correctly abstained
    }}}
    m = score_adapter_a(gold, preds)
    assert m["_counts"]["hall"] == [2, 3]          # int_W_cm + has_liner of 3 gaps
    assert m["hallucination_rate"] == round(2 / 3, 4)
    assert m["_counts"]["bool"][1] == 1            # has_liner is also a boolean FP


def test_adapter_a_perfect_predictions_zero_hallucination():
    gold = [{"id": "y", "input": "bag 90x90x120", "output": {
        "ext_L_cm": {"value": 90, "state": "provided"},
        "sf": {"value": None, "state": "not_specified"},
        "customer": {"value": None, "state": "not_specified"}}}]
    m = score_adapter_a(gold, {"y": {"output": gold[0]["output"]}})
    assert m["hallucination_rate"] == 0.0


def test_adapter_b_gsm_within_one_step():
    gold = [{"id": "y", "output": {"family": "u_panel", "body_gsm": 150}}]
    preds = {"y": {"output": {"family": "u_panel", "body_gsm": 155}}}   # next in catalogue
    m = score_adapter_b(gold, preds)
    assert m["family_accuracy"] == 1.0
    assert m["body_gsm_exact"] == 0.0
    assert m["body_gsm_within_1_step"] == 1.0


def test_gate_check_hard_fail():
    rows, hard_ok = check_gates({"hallucination_rate": 0.05}, GATES_A)
    assert hard_ok is False
    assert any(r[0] == "hallucination_rate" and r[4] == "FAIL" for r in rows)
