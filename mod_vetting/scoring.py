"""Score computation from stage-2 booleans -- deterministic, no model calls.

Mirrors implementation-spec.md section 2. Kept as plain functions over a
dict of answers so they're trivially unit-testable without any pipeline
machinery around them.
"""

from __future__ import annotations


def conduct_level(a: dict) -> int | None:
    if not (a.get("c1") and a.get("c2") and a.get("c3") and a.get("c4")):
        return None  # cleared
    if a.get("c5") is False:
        return 1  # responding, not initiating
    return 3  # base; stage 3 (unimplemented) would adjust for pattern


def bias_level(a: dict) -> int | None:
    if not (a.get("b1") and a.get("b2") and a.get("b3")):
        return None
    return 3 if a.get("b4") else 2


def judgment_level(a: dict) -> int | None:
    if not (a.get("j1") and a.get("j2")):
        return None
    return 4 if a.get("j4") else (2 if a.get("j3") else 1)


def coordination_level(a: dict) -> int | None:
    if not (a.get("co1") and a.get("co2") and a.get("co3")):
        return None
    return 3 if a.get("co4") else 2


def doxxing_triggered(a: dict) -> bool:
    """Binary, not graduated -- there is no 'mild' doxxing (spec section 2)."""
    return bool(a.get("d1") and a.get("d2") and a.get("d3"))


CATEGORY_LEVEL_FNS = {
    "conduct": conduct_level,
    "bias": bias_level,
    "judgment": judgment_level,
    "coordination": coordination_level,
}


def score_all(answers: dict) -> dict:
    """Returns {category: level_or_None} for the four graduated categories,
    plus doxxing_triggered as a separate boolean (see spec section 2)."""
    result = {cat: fn(answers) for cat, fn in CATEGORY_LEVEL_FNS.items()}
    result["doxxing_triggered"] = doxxing_triggered(answers)
    return result
