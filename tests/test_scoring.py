from mod_vetting.scoring import (
    bias_level,
    conduct_level,
    coordination_level,
    doxxing_triggered,
    judgment_level,
)


def test_conduct_cleared_when_not_all_true():
    assert conduct_level({"c1": True, "c2": True, "c3": True, "c4": False}) is None
    assert conduct_level({"c1": True, "c2": None, "c3": True, "c4": True}) is None


def test_conduct_level_1_when_responding_not_initiating():
    a = {"c1": True, "c2": True, "c3": True, "c4": True, "c5": False}
    assert conduct_level(a) == 1


def test_conduct_level_3_base_case():
    a = {"c1": True, "c2": True, "c3": True, "c4": True, "c5": True}
    assert conduct_level(a) == 3
    a2 = {"c1": True, "c2": True, "c3": True, "c4": True, "c5": None}
    assert conduct_level(a2) == 3  # null c5 (no parent context) still bases at 3


def test_bias_cleared_and_levels():
    assert bias_level({"b1": True, "b2": True, "b3": False}) is None
    assert bias_level({"b1": True, "b2": True, "b3": True, "b4": False}) == 2
    assert bias_level({"b1": True, "b2": True, "b3": True, "b4": True}) == 3


def test_judgment_cleared_and_levels():
    assert judgment_level({"j1": True, "j2": False}) is None
    assert judgment_level({"j1": True, "j2": True, "j3": None, "j4": None}) == 1
    assert judgment_level({"j1": True, "j2": True, "j3": True, "j4": False}) == 2
    assert judgment_level({"j1": True, "j2": True, "j3": True, "j4": True}) == 4


def test_judgment_j4_null_does_not_escalate():
    # commenter never replied again in the captured window -- j4 must be
    # null, not False, and null must not be treated as "corrected + dropped"
    a = {"j1": True, "j2": True, "j3": True, "j4": None}
    assert judgment_level(a) == 2  # falls to the j3-only tier, not level 4


def test_coordination_cleared_and_levels():
    assert coordination_level({"co1": True, "co2": True, "co3": False}) is None
    assert coordination_level({"co1": True, "co2": True, "co3": True, "co4": False}) == 2
    assert coordination_level({"co1": True, "co2": True, "co3": True, "co4": True}) == 3


def test_doxxing_is_binary_not_graduated():
    assert doxxing_triggered({"d1": True, "d2": True, "d3": True}) is True
    assert doxxing_triggered({"d1": True, "d2": True, "d3": False}) is False
    assert doxxing_triggered({"d1": True, "d2": False, "d3": True}) is False
    assert doxxing_triggered({}) is False
