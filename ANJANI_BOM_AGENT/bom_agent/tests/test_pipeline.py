"""End-to-end pipeline on the 85x85x85 reference — deterministic, no GPU/model."""
from bom_agent.pipeline import run

REF = ("U PANNEL BAG 85X85X85 CM, SWL 1000 KG, SF 5:1, WEIGHT 880 G, "
       "4 corner loop 50 mm belt, free height 25 cm, open top, flat bottom, colour white")


def test_reference_bag_runs_end_to_end():
    r = run(REF)
    assert r.build_spec["family"] == "u_panel"
    assert r.build_spec["loop_type"] == "corner"
    assert r.physical_bom["grand_total_g"] is not None
    # H5 presentation contract
    assert r.meta["presentation_order"][0] == "construction_type"


def test_gsm_not_started_below_chart_floor_without_customer_gsm():
    r = run(REF)
    env = r.meta["envelope"]
    if env.get("gsm_floor"):
        assert r.build_spec["body_gsm"] >= env["gsm_floor"], \
            "solver/config must not sit below the chart floor with no C6 override"


def test_clarifications_are_raised_for_missing_fields():
    r = run(REF)
    codes = {c["code"] for c in r.clarification["advisory"] + r.clarification["blocking"]}
    assert "PRODUCT_NOT_STATED" in codes          # C1
    assert "LOOP_LENGTH_ASSUMED" in codes         # D1


def test_backward_mode_selected_when_weight_given():
    r = run(REF)
    assert r.meta["solver"]["mode"] == "backward"
