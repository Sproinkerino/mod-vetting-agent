"""Grounding gate -- implementation-spec.md section 3.

A finding's quote is only trusted if it is an exact substring of the
comment body actually stored in the corpus. No normalization on either
side: the string shown to the model and the string checked here must be
byte-identical, or the hallucination-rate metric this gate produces
becomes meaningless (see the "Normalization contract" note in the spec).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CorpusItem:
    id: str
    body: str
    permalink: str


@dataclass
class Finding:
    id: str  # comment id this finding is about
    model_id: str
    quotes: dict[str, str | None]  # category -> quote or None
    answers: dict
    grounded_quotes: dict = field(default_factory=dict)
    permalink: str | None = None


class Metrics:
    """Minimal counter sink. Swap for statsd/prometheus in production; the
    grounding gate only needs .incr(name, **tags)."""

    def __init__(self):
        self.counts: dict[tuple, int] = {}

    def incr(self, name: str, **tags):
        key = (name, tuple(sorted(tags.items())))
        self.counts[key] = self.counts.get(key, 0) + 1

    def get(self, name: str, **tags) -> int:
        key = (name, tuple(sorted(tags.items())))
        return self.counts.get(key, 0)


def ground(
    findings: list[Finding], corpus: dict[str, CorpusItem], metrics: Metrics | None = None
) -> tuple[list[Finding], list[tuple[Finding, str | None, str]]]:
    """Returns (kept, dropped). dropped entries are (finding, category, reason)."""
    metrics = metrics or Metrics()
    kept, dropped = [], []

    for f in findings:
        item = corpus.get(f.id)
        if item is None:
            dropped.append((f, None, "unknown_item"))
            metrics.incr("hallucinated_quote", model=f.model_id, category="unknown_item")
            continue

        any_quote_attempted = False
        for category, quote in f.quotes.items():
            if quote is None:
                continue
            any_quote_attempted = True
            if quote not in item.body:
                dropped.append((f, category, "hallucinated_quote"))
                metrics.incr("hallucinated_quote", model=f.model_id, category=category)
                continue
            f.grounded_quotes[category] = {
                "quote": quote,
                "offset": item.body.index(quote),
            }

        if not f.grounded_quotes:
            # Only log a separate "no_quote" when nothing was even attempted --
            # a finding where every quote was hallucinated is already fully
            # accounted for by the per-category hallucinated_quote entries
            # above; double-logging it would inflate both counters for the
            # same underlying event.
            if not any_quote_attempted:
                dropped.append((f, None, "no_quote"))
            continue

        f.permalink = item.permalink
        kept.append(f)

    return kept, dropped


def hallucination_rate(dropped: list[tuple], total_quotes_checked: int) -> float:
    """total_quotes_checked should count every non-null quote field seen,
    not every finding -- a finding with 3 quotes and 1 hallucinated one
    contributes 1/3, not 1/1."""
    hallucinated = sum(1 for _, _, reason in dropped if reason == "hallucinated_quote")
    if total_quotes_checked == 0:
        return 0.0
    return hallucinated / total_quotes_checked
