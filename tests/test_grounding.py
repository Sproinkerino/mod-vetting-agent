from mod_vetting.grounding import CorpusItem, Finding, Metrics, ground, hallucination_rate


def make_corpus(**items):
    return {id_: CorpusItem(id=id_, body=body, permalink=f"https://reddit.com/{id_}") for id_, body in items.items()}


def test_exact_substring_kept():
    corpus = make_corpus(t1="You are wrong about that rule, actually.")
    f = Finding(id="t1", model_id="m1", quotes={"judgment": "wrong about that rule"}, answers={})
    kept, dropped = ground([f], corpus)
    assert len(kept) == 1
    assert dropped == []
    assert kept[0].grounded_quotes["judgment"]["offset"] == 8


def test_non_substring_dropped_as_hallucinated():
    corpus = make_corpus(t1="You are wrong about that rule, actually.")
    f = Finding(id="t1", model_id="m1", quotes={"judgment": "you are incorrect"}, answers={})
    kept, dropped = ground([f], corpus)
    assert kept == []
    # exactly one drop event: the hallucinated_quote for "judgment", not a
    # second "no_quote" for the same finding (see grounding.py comment)
    assert len(dropped) == 1
    assert dropped[0][2] == "hallucinated_quote"


def test_null_quote_for_a_category_is_skipped_not_dropped():
    corpus = make_corpus(t1="Get out of here, idiot.")
    f = Finding(
        id="t1", model_id="m1",
        quotes={"conduct": "Get out of here, idiot.", "bias": None, "judgment": None},
        answers={},
    )
    kept, dropped = ground([f], corpus)
    assert len(kept) == 1
    assert "conduct" in kept[0].grounded_quotes
    assert dropped == []


def test_all_quotes_null_is_dropped_as_no_quote():
    corpus = make_corpus(t1="whatever")
    f = Finding(id="t1", model_id="m1", quotes={"conduct": None}, answers={})
    kept, dropped = ground([f], corpus)
    assert kept == []
    assert dropped[0][2] == "no_quote"


def test_partial_hallucination_multi_category():
    # one real quote (conduct), one fabricated quote (bias) on the same finding
    corpus = make_corpus(t1="Get out of here, idiot. Also, all of you people are like that.")
    f = Finding(
        id="t1", model_id="m1",
        quotes={
            "conduct": "Get out of here, idiot.",
            "bias": "you people are all criminals",  # not actually in the body
        },
        answers={},
    )
    kept, dropped = ground([f], corpus)
    assert len(kept) == 1  # survives because conduct grounded, even though bias didn't
    assert "conduct" in kept[0].grounded_quotes
    assert "bias" not in kept[0].grounded_quotes
    assert len(dropped) == 1
    assert dropped[0][1] == "bias"


def test_normalization_mismatch_is_indistinguishable_from_hallucination():
    """Documents the exact failure mode the spec's normalization contract
    warns about: a curly quote in the model's copy vs a straight quote in
    the corpus reads as a hallucination even though the model copied it
    faithfully from what it was shown. This is why prompt text and corpus
    text must be the same string end to end -- this test is not asserting
    desired behavior, it's pinning the danger so nobody "fixes" it by
    fuzzy-matching (which would defeat the exact-substring guarantee)."""
    corpus = make_corpus(t1='She said "that’s not true" in the thread.')  # curly apostrophe
    f = Finding(id="t1", model_id="m1", quotes={"conduct": "that's not true"}, answers={})  # straight
    kept, dropped = ground([f], corpus)
    assert kept == []
    assert dropped[0][2] == "hallucinated_quote"


def test_hallucination_rate_counts_per_quote_not_per_finding():
    metrics = Metrics()
    corpus = make_corpus(t1="one two three")
    f = Finding(
        id="t1", model_id="m1",
        quotes={"conduct": "one two", "bias": "not present", "judgment": "three"},
        answers={},
    )
    kept, dropped = ground([f], corpus, metrics)
    # 3 quotes checked, 1 hallucinated -> rate should be 1/3, not 1/1
    rate = hallucination_rate(dropped, total_quotes_checked=3)
    assert abs(rate - (1 / 3)) < 1e-9
    assert metrics.get("hallucinated_quote", model="m1", category="bias") == 1
