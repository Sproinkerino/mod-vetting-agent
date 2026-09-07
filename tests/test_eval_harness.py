from mod_vetting.eval_harness import (
    cohens_kappa,
    finding_set_overlap,
    hallucinated_quote_rate,
    position_consistency,
    repetition_stability,
    triage_recall_audit,
)


def test_kappa_perfect_agreement():
    assert cohens_kappa([1, 2, 3, 1, 2], [1, 2, 3, 1, 2]) == 1.0


def test_kappa_chance_level_agreement_near_zero():
    # two raters that just happen to agree at the rate chance alone
    # would predict should score near 0, not the raw ~50% match rate
    a = [0, 0, 0, 0, 1, 1, 1, 1]
    b = [0, 1, 0, 1, 0, 1, 0, 1]  # independent of a, 50% raw match
    k = cohens_kappa(a, b)
    assert -0.3 < k < 0.3  # near zero, not near the raw 0.5 agreement rate


def test_kappa_raw_agreement_overstates_on_skewed_distribution():
    # spec's exact claim: raw exact-match overstates real discriminative
    # ability on a skewed label distribution. Almost everything is 0
    # (cleared) for both raters, one real disagreement on the only
    # nonzero item -- raw agreement looks great, kappa should be much lower.
    a = [0] * 18 + [3]
    b = [0] * 18 + [1]  # disagree on the one substantive case
    raw_agreement = sum(1 for x, y in zip(a, b) if x == y) / len(a)
    k = cohens_kappa(a, b)
    assert raw_agreement > 0.9
    assert k < raw_agreement  # kappa must correct downward, not match raw


def test_finding_set_overlap_identical_and_disjoint():
    assert finding_set_overlap({"a", "b"}, {"a", "b"}) == 1.0
    assert finding_set_overlap({"a"}, {"b"}) == 0.0
    assert finding_set_overlap(set(), set()) == 1.0  # both empty = trivially identical


def test_finding_set_overlap_partial():
    assert finding_set_overlap({"a", "b", "c"}, {"b", "c", "d"}) == 2 / 4


def test_repetition_stability_gate():
    runs = [{"a", "b"}, {"a", "b"}, {"a", "b", "c"}]  # 2/3 pairs identical, one has an extra
    result = repetition_stability(runs, gate=0.90)
    assert result["passed"] is False  # {"a","b"} vs {"a","b","c"} overlap = 2/3 < 0.90
    assert len(result["pairs"]) == 3


def test_position_consistency_requires_exact_match_not_just_overlap():
    result = position_consistency({"a", "b", "c"}, {"a", "b"})  # 2/3 overlap, not exact
    assert result["passed"] is False
    result2 = position_consistency({"a", "b"}, {"a", "b"})
    assert result2["passed"] is True


def test_hallucinated_quote_rate_gate():
    dropped = [(None, "conduct", "hallucinated_quote")]
    result = hallucinated_quote_rate(dropped, total_quotes_checked=1000, gate=0.005)
    assert result["rate"] == 0.001
    assert result["passed"] is True

    result2 = hallucinated_quote_rate(dropped, total_quotes_checked=100, gate=0.005)
    assert result2["rate"] == 0.01
    assert result2["passed"] is False


def test_triage_recall_audit_catches_missed_upheld():
    result = triage_recall_audit(unflagged_ids=["a", "b", "c"], manually_found_upheld_ids=["b"])
    assert result["passed"] is False
    assert result["missed_ids"] == ["b"]

    clean = triage_recall_audit(unflagged_ids=["a", "b", "c"], manually_found_upheld_ids=[])
    assert clean["passed"] is True
