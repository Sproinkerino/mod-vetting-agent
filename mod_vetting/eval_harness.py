"""Eval harness mechanics. implementation-spec.md section 7.

This module implements the METRICS, not the golden set itself -- a real
golden set of 15-20 hand-scored past applicants has to come from actual
human judgment on actual past cases, which doesn't exist yet and can't be
fabricated here. Wire this up against real hand-scored data when it
exists; tests/test_eval_harness.py exercises the math against synthetic
labels so the formulas themselves are trustworthy before that data does.
"""

from __future__ import annotations

from collections import Counter


def cohens_kappa(rater_a: list, rater_b: list) -> float:
    """Chance-corrected agreement -- raw exact-match overstates a judge's
    real discriminative ability on a skewed label distribution (spec
    section 7). rater_a/rater_b: parallel lists of labels (e.g. score
    levels) for the same items in the same order."""
    if len(rater_a) != len(rater_b):
        raise ValueError("rater_a and rater_b must be the same length")
    n = len(rater_a)
    if n == 0:
        return 0.0

    observed_agreement = sum(1 for a, b in zip(rater_a, rater_b) if a == b) / n

    labels = set(rater_a) | set(rater_b)
    count_a = Counter(rater_a)
    count_b = Counter(rater_b)
    expected_agreement = sum((count_a[label] / n) * (count_b[label] / n) for label in labels)

    if expected_agreement == 1.0:
        return 1.0  # both raters used exactly one label -- perfect, undefined denominator otherwise
    return (observed_agreement - expected_agreement) / (1 - expected_agreement)


def finding_set_overlap(run_a: set, run_b: set) -> float:
    """Jaccard overlap between two runs' finding-id sets on the same
    input. Spec section 7 originally gated repetition-stability on exact
    identity across 3 runs; softened to this overlap metric with a 90%
    default gate since temp=0 hosted APIs aren't reliably bit-
    reproducible -- see implementation-spec.md revision notes."""
    if not run_a and not run_b:
        return 1.0
    union = run_a | run_b
    if not union:
        return 1.0
    return len(run_a & run_b) / len(union)


def repetition_stability(runs: list[set], gate: float = 0.90) -> dict:
    """runs: finding-id sets from N runs of the same input. Returns
    pairwise overlaps and whether every pair clears the gate."""
    pairs = []
    for i in range(len(runs)):
        for j in range(i + 1, len(runs)):
            pairs.append({"i": i, "j": j, "overlap": finding_set_overlap(runs[i], runs[j])})
    passed = all(p["overlap"] >= gate for p in pairs)
    return {"pairs": pairs, "gate": gate, "passed": passed}


def position_consistency(shuffled_run_a: set, shuffled_run_b: set) -> dict:
    """Same batch, two different orderings -- flag sets should match
    (spec section 1/7). Reuses the overlap metric; gate is stricter here
    (1.0, exact match expected) since this isn't about sampling
    nondeterminism, it's specifically testing for position bias."""
    overlap = finding_set_overlap(shuffled_run_a, shuffled_run_b)
    return {"overlap": overlap, "passed": overlap == 1.0}


def hallucinated_quote_rate(dropped: list[tuple], total_quotes_checked: int, gate: float = 0.005) -> dict:
    """Wraps grounding.hallucination_rate with the eval-harness gate
    (spec section 7: <= 0.5%)."""
    from .grounding import hallucination_rate

    rate = hallucination_rate(dropped, total_quotes_checked)
    return {"rate": rate, "gate": gate, "passed": rate <= gate}


def triage_recall_audit(unflagged_ids: list[str], manually_found_upheld_ids: list[str]) -> dict:
    """manually_found_upheld_ids: ids a human found, on manual review of a
    sample of UNFLAGGED comments, that should have been flagged (spec:
    'Manual audit of unflagged sample -- no missed uphelds'). Any overlap
    with unflagged_ids is a real miss."""
    missed = [i for i in manually_found_upheld_ids if i in unflagged_ids]
    return {"missed_count": len(missed), "missed_ids": missed, "passed": len(missed) == 0}
