# mod-vetting-agent

Implementation of `implementation-spec.md` (the fixed version — see its
own "Revision notes" section for what was fixed/dropped from the
original spec before this was built, and this README for what changed
*during* the build itself).

## What this is

A pipeline that reviews a moderator applicant's public Reddit history
against a subreddit's rules and produces a cited, evidence-based report:
scores per category (conduct/bias/judgment/coordination), hard-fail flags
(hate_speech/targeted_harassment/doxxing/vote_manipulation), and every
claim backed by an exact, verified quote and permalink. It does not make
the moderation decision — see spec section 0 and section 8. A named human
reviews every report before it can circulate.

**This produces real adverse-claims documents about real, identifiable
people.** Point it only at actual applicants under actual consideration,
with actual subreddit rules supplied — not at arbitrary usernames.

## Build status

Implements build order steps 1–5 and 7 from the spec:

| Stage | Status |
|---|---|
| 0. Fetch (applicant history + thread context) | ✅ `mod_vetting/fetch.py` |
| Grounding gate + tests | ✅ `mod_vetting/grounding.py` |
| 1. Triage | ✅ `mod_vetting/stage1_triage.py` |
| 2. Adjudicate | ✅ `mod_vetting/stage2_adjudicate.py` |
| Scoring | ✅ `mod_vetting/scoring.py` |
| Report assembly + human gate | ✅ `mod_vetting/report.py` |
| Orchestrator | ✅ `mod_vetting/orchestrator.py` — stops at `awaiting_human` |
| Renderer | ✅ `mod_vetting/render.py` |
| Eval harness (metrics) | ✅ `mod_vetting/eval_harness.py` — **mechanics only, no real golden set** |
| 3–5. Synthesise / steelman / reconcile | ❌ not implemented — no prompt spec exists for these stages (the implementation spec explicitly supersedes only stages 1–2 of a separate design doc). The orchestrator routes straight from grounding to `awaiting_human` instead of fabricating them. |

## What changed while building (beyond the spec-review pass)

Found during actual implementation, not the earlier spec review:

- **`claude-sonnet-5` rejects `temperature`** ("deprecated for this
  model") **and assistant-message prefill** ("This model does not
  support assistant message prefill"). Both are extended-thinking-family
  constraints not mentioned in the spec, which calls for "temp 0" and
  implies prefill-style JSON coercion. Switched both stages to **forced
  tool-use** (`tool_choice` pinned to a tool whose `input_schema` is the
  desired output shape) instead — more reliable than prefill regardless,
  and works on both models. Temperature is no longer sent at all; this
  matters for the eval harness's repetition-stability numbers (see
  `eval_harness.py`).
- **Reddit's own `/comments/<id>.json` is login-walled** as of this
  build (403, then a redirect to a login page). Thread context (parent +
  replies, needed for j3/j4/d3) now comes entirely from Arctic Shift's
  `/api/comments/ids` and `/api/comments/tree` instead, which are open.
- **Arctic Shift's `/api/comments/tree` returns Reddit's nested listing
  shape**, not a flat list — the first version of the tree parser only
  saw top-level comments and silently reported "0 replies" for anything
  nested. Fixed (`fetch._flatten_tree`) and regression-tested
  (`tests/test_fetch.py`).
- **A comment outside the tree fetch's window (megathreads) was silently
  treated as "confirmed zero replies"** rather than "unknown." Fixed to
  raise `ThreadContextUnavailable` in that case, same as a network
  failure — the caller records it and the model answers j3/j4/d3 as
  `null` with a reason, rather than a confident false negative.
- **A grounding double-count bug**: a finding where every quote was
  hallucinated (not null, just wrong) was logged both as
  `hallucinated_quote` per category *and* as `no_quote` overall, double-
  counting the same event. Fixed and tested
  (`tests/test_grounding.py::test_non_substring_dropped_as_hallucinated`).
- **`report.schema.json`'s `state` enum never listed `awaiting_human`**,
  even though spec section 8 says jobs "render to `awaiting_human`."
  Schema validation caught its own spec's inconsistency. Fixed in both
  the schema and `implementation-spec.md` itself.

## Known gaps, honestly

- `applicant.account_age_days`, `sub_tenure_days`, `comments_in_sub`,
  `subs_modded` are stubbed to `0` in `cli.py` with `TODO`s — computing
  them needs data this build doesn't fetch (join date isn't in Arctic
  Shift's author-search response; sub-tenure/comments-in-sub need a
  target-subreddit filter the CLI doesn't take yet; subs-modded needs a
  moderator-list lookup this doesn't do). Don't trust those four fields
  in a report until that's wired up.
- `hard_fails` level→trigger thresholds (`report.py:HARD_FAIL_RULES`) are
  this build's own policy choice, not something the spec pins down
  beyond the four code names. Read and adjust deliberately before using
  this for real decisions.
- The eval harness has real math (tested against synthetic labels in
  `tests/test_eval_harness.py`) but no real golden set — that requires
  actual humans hand-scoring actual past applicants, which nothing here
  can fabricate.
- `orchestrator.run_job` doesn't resume mid-job from storage on this
  build's first pass — checkpoints are written (and the idempotency
  ledger is there and tested), but a re-invocation always restarts from
  `fetching`. Wiring real resume is separable follow-up work.

## Running it

```bash
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# offline unit tests (no API key needed, no network for most of them)
pytest tests/ -v

# integration test against the real Anthropic API, synthetic (not-a-real-person) content
ANTHROPIC_API_KEY=... pytest tests/test_orchestrator_integration.py -v

# a real run
ANTHROPIC_API_KEY=... python cli.py <username> --rules rules.txt --register register.txt
```
