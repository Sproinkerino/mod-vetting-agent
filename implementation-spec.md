# Implementation Spec — Prompts, Schema, Orchestrator

Supersedes stage 1–2 sketches in `mod-vetting-agent-design.md`. Two design changes from that draft, both driven by current practice on rubric-based judging:

1. **Stage 2 no longer asks a model for a 0–5 score.** It answers narrow yes/no questions about one comment, and code computes the score from the booleans. Decomposing rubrics into discrete checks is the main lever against judge variance, and it makes disagreement debuggable — you can see exactly which criterion flipped.
2. **The pinned contract is now three values, not two:** `(model_id, rubric_version, prompt_template_hash)`. A prompt edit changes scores as surely as a model swap does.

---

## Revision notes (this pass)

Fixes applied after a close read, and what got dropped instead of patched:

**Fixed:**
- `j3`/`j4` (JUDGMENT: was the assertion corrected, did the commenter maintain it after) were unanswerable — the stage 2 template only supplied the parent comment, never what came after. Added a `subsequent_replies` block to the template.
- `hard_fails.doxxing` and `hard_fails.vote_manipulation` had no adjudication behind them — stage 2 had no boolean group for either. Added a DOXXING group and a COORDINATION group (stage 1 already had a `coordination` triage flag with nowhere to land).
- Stage 2 emitted one `quote` for the whole comment, but a single comment can trigger conduct *and* bias *and* judgment findings off different spans. `quote` is now a map keyed by category.
- Grounding's exact-substring check had no normalization contract. Added one: the string shown to the model and the string in `corpus` must be byte-identical, full stop.
- `self_description` existed both as a singular root object and as a `findings[]` category. Dropped the singular object; it's a findings category like everything else now.
- `confidence` in stage 1 output was collected and never used. Wired it to an ongoing QA sample (see §7) instead of dropping it — it was the cheapest available signal for the "recall drift between eval cycles" gap.
- "Repetition stability: identical findings across 3 runs" is not a realistic gate for temp=0 hosted APIs (provider-side batching/routing means temp=0 isn't always bit-reproducible). Softened to an overlap threshold, to be checked empirically in build step 5 before trusting it.
- `report.state`'s enum (section 4) never listed `awaiting_human`, even though section 8 says jobs "render to `awaiting_human`" and the orchestrator's own state machine (section 5) has it as a stage. Found while building the report assembler -- schema validation rejected its own spec's stated behavior. Added it to the enum.
- **Found while building the frontend against this schema:** `findings[]` carried `quote` + `quote_offset` but never the full comment `body` an offset is supposed to index into, nor `parent_body`/`replies` for context. Useless without them -- the frontend can't highlight a quote inside a body it never receives. Added `body`, `parent_body`, `replies` to the findings schema and threaded them through `stage2_adjudicate.AdjudicationOutcome` -> `orchestrator.corpus_meta` -> `report.build_findings`.
- **Not in the original spec, found during build:** `claude-sonnet-5` rejects both `temperature` ("deprecated for this model") and assistant-message prefill ("This model does not support assistant message prefill") -- both are extended-thinking-family constraints. The spec's "temp 0" for stage 2 (section 2 header) and the prefill-for-JSON approach implied by the report schema's structure don't work against the actual pinned model. Switched both stages to forced tool-use (a tool with `input_schema` matching the desired output, `tool_choice` forced to it) instead of prompt-level JSON coercion -- more robust than prefill anyway, and works on both models. Temperature is no longer sent at all; determinism for section 7's repetition-stability gate now depends on whatever the model's default (non-configurable) behavior is, not an explicit temp=0 -- worth knowing before trusting that gate's numbers.

**Dropped, not fixed:**
- `hard_fails.undisclosed_coi` and `hard_fails.application_dishonesty`. Both require data this pipeline never ingests — the applicant's actual application answers, and other subreddits' mod rosters — to compare against observed behavior. Nothing in stage 1 or stage 2 can produce either from comment text alone. Removed from the v1 enum rather than leave dead codes that read as "checked, clean" when they were never checked. Re-add when there's an application-cross-check stage to back them.

---

## 0. This is a workflow, not an agent

Anthropic's distinction: workflows run LLMs through predefined code paths; agents let the model direct its own process. Autonomy is the wrong trade here. Every applicant must traverse identical steps in identical order or the reports aren't comparable, and "the model decided to look into something" is not a defensible line in a document that makes adverse claims about a named person.

The only agentic property retained is **context isolation via fan-out**: workers burn tokens on raw material, the orchestrator receives condensed verified findings. Same reason Claude Code dispatches subagents for search.

---

## 1. Stage 1 — Triage

**Model** `claude-haiku-4-5` · **temp** 0 · **max_tokens** 4096 · batch of 50 · `response_format` JSON

### System

```
You are a triage filter in a moderator-application review pipeline. You
process batches of public Reddit comments and mark which ones a later
stage should examine in full thread context.

You are not judging anyone. You do not decide anything. You route.

Optimise for recall. A later stage has the parent comments and will clear
false positives cheaply. A comment you skip is never seen again. When
unsure, flag it.

Flags:

  hostility_individual
    Insult, mockery, contempt, or an attack aimed at a person.
    Flag regardless of whether it looks deserved or reciprocal.

  hostility_group
    A generalisation, slur, or hostility aimed at a group of people.
    Flag whether or not the group is a protected class.

  rule_reasoning
    Reasoning about rules, moderation, enforcement, or what should be
    allowed. Includes rule assertions and complaints about mod actions.

  self_description
    States their own occupation, industry, employer type, or affiliation.

  coordination
    Organising votes, pile-ons, or cross-subreddit action.

  doxxing
    Shares or solicits another identifiable person's private information:
    real name, address, employer, phone number, or other identifying
    detail not already made public by that person in the same thread.

  factual_assertion
    States a rule or fact as settled, in a way another user could rely on.

A comment may carry several flags. Emit none for comments carrying none;
most comments carry none.

Output JSON only. No prose, no markdown fence.

[{"id": "t1_...", "flags": ["hostility_individual"], "confidence": 0.7}]
```

### User template

```
Batch {batch_id}. Comments are in randomised order.

<comments>
{% for c in comments %}
<comment id="{{c.id}}">{{c.body}}</comment>
{% endfor %}
</comments>
```

**Randomise order within each batch.** Judge models show position bias — a tendency to score by location in the prompt rather than content. Shuffling makes it measurable: run the same batch twice with different orderings and the flag sets should match. Divergence is your position-consistency metric.

**Expected flag rate: 8–20%.** Under 2% means the prompt has drifted conservative and you are losing recall silently. Alert on it. Adding the `doxxing` flag may shift this slightly; re-baseline empirically rather than assuming the old range still holds.

**`confidence` is not decorative.** Route flagged items with `confidence < 0.4` into the ongoing QA sample described in §7, alongside the unflagged-sample audit. It's the cheapest signal available for catching recall drift between formal eval runs, and it was previously collected and discarded.

---

## 2. Stage 2 — Adjudicate

**Model** `claude-sonnet-5` · **temp** 0 · one call per flagged comment · concurrency cap 20

The model answers factual questions about one comment. It never assigns a score.

### System

```
You answer specific factual questions about a single Reddit comment, using
the thread context provided. Another system computes scores from your
answers. You do not score, rank, or characterise the person.

Read the parent comment before the comment itself, and the subsequent
replies (if any) after it. Most false positives in this pipeline come from
judging text without what it replied to; most wrong JUDGMENT answers come
from not seeing what happened after it.

Answer only from what is in front of you. If a question cannot be answered
from the provided context, answer null. Never infer intent, never guess at
what the person believes, never reason about who they are.

QUOTATION RULE — this is enforced downstream and non-negotiable.
Every quote field must be copied character-for-character from the comment
body, exactly as given to you below -- no cleanup, no re-typing, no fixing
spelling or punctuation, no normalising quote marks or whitespace. Copy
the substring exactly as it appears in <comment_under_review>. Do not
paraphrase into it. Do not splice non-adjacent text. If no exact
contiguous span supports a finding, set that quote to null and the
finding will be dropped.

A comment can trigger findings in more than one category off different
spans (e.g. an insult in one sentence, a rule assertion in another).
Give each category its own quote -- do not reuse one span to support
an unrelated category, and do not merge two categories under one span
unless the same exact text genuinely supports both.

Answer every question with true, false, or null.

CONDUCT
 c1  Contains an insult, slur, mockery, or expression of contempt.
 c2  That contempt is aimed at a specific person, not an idea, object,
     institution, or the commenter themselves.
 c3  It is the commenter's own speech — not quoted, reported, or
     attributed to someone else.
 c4  It is in earnest — not the subreddit's established joking register,
     not mutual banter both parties are clearly playing along with.
 c5  The commenter initiated or escalated, rather than responding to an
     attack on themselves in the parent.

BIAS
 b1  References a group by a protected attribute: race, ethnicity,
     religion, nationality, gender, sexuality, disability, age.
 b2  Attaches a negative generalisation or hostility to that group.
 b3  It is the commenter's own speech, in earnest (c3 and c4 both hold).
 b4  Aimed at a specific person on the basis of their membership in it.

JUDGMENT
 j1  Asserts a rule, policy, or fact as settled.
 j2  The assertion is incorrect, checked against the subreddit rules given.
 j3  A reply in the provided thread continuation corrects it, with a
     specific counter-claim -- not just disagreement in tone.
 j4  The commenter posted again in the same continuation after that
     correction and repeated or did not retract the original assertion.
     If the commenter never replied again in the given continuation,
     answer null, not false -- you cannot distinguish "accepted the
     correction silently" from "never saw it."

COORDINATION
 co1  Explicitly asks others to vote, comment, report, or otherwise act
      on a specific post, comment, or user, rather than describing their
      own intended action.
 co2  It is the commenter's own speech, in earnest (c3 and c4 both hold,
      read against this comment).
 co3  The ask is aimed at influencing an outcome (a vote count, a report
      queue, a specific decision) rather than open discussion, a shared
      link, or organising an on-platform event/AMA.
 co4  Names or clearly identifies the specific target (a user, a post, a
      thread) rather than speaking in general terms.

DOXXING
 d1  Contains a real name, address, employer, phone number, email, or
     other detail that could identify a specific real person beyond
     their Reddit username.
 d2  That person is someone other than the commenter themselves.
 d3  The information was not already shared by that same person, in
     their own words, earlier in the same thread continuation you were
     given.

SELF-DESCRIPTION
 s1  States their own occupation, industry, or professional affiliation.

Output JSON only:

{
  "id": "t1_...",
  "answers": {"c1": true, "c2": true, "c3": true, "c4": false, "c5": null,
              "b1": false, "b2": null, "b3": null, "b4": null,
              "j1": false, "j2": null, "j3": null, "j4": null,
              "co1": false, "co2": null, "co3": null, "co4": null,
              "d1": false, "d2": null, "d3": null,
              "s1": false},
  "quotes": {"conduct": "exact contiguous span or null",
             "bias": null,
             "judgment": null,
             "coordination": null,
             "doxxing": null,
             "self_description": null},
  "context_note": "one sentence on what the parent establishes, or null",
  "register_note": "one sentence if the subreddit's norms affect reading"
}
```

### User template

```
<subreddit_rules>
{{ rules }}
</subreddit_rules>

<subreddit_register>
{{ register_notes }}
</subreddit_register>

<parent_comment>
{{ parent_body or "[top-level post, no parent]" }}
</parent_comment>

<comment_under_review>
{{ body }}
</comment_under_review>

<subsequent_replies>
{% if replies %}
{% for r in replies %}
<reply id="{{r.id}}" author_is_commenter="{{r.author == comment.author}}">{{r.body}}</reply>
{% endfor %}
{% else %}
[no replies captured in this thread continuation]
{% endif %}
</subsequent_replies>
```

`subsequent_replies` is capped at a fixed depth/breadth from the fetch layer (e.g. direct replies plus one level down) — it is a window, not the full downstream thread. j3/j4 and d3 are answered against what's in that window; `null` is the correct answer, not `false`, when the window doesn't settle the question. Don't let the model guess past the edge of what it was given.

`register_notes` is a short human-written description of the sub's house style — running jokes, ritual insults, terms that read as hostile from outside. Without it the pipeline flags every sub's in-joke as an attack, for every applicant, forever. This is the highest-value hand-written asset in the system and it takes twenty minutes to write.

### Score computation — code, not model

```python
def conduct_level(a):
    if not (a.c1 and a.c2 and a.c3 and a.c4):
        return None                      # cleared
    if a.c5 is False:
        return 1                         # responding, not initiating
    return 3                             # base; stage 3 adjusts for pattern

def bias_level(a):
    if not (a.b1 and a.b2 and a.b3):
        return None
    return 3 if a.b4 else 2

def judgment_level(a):
    if not (a.j1 and a.j2):
        return None
    return 4 if a.j4 else (2 if a.j3 else 1)

def coordination_level(a):
    if not (a.co1 and a.co2 and a.co3):
        return None
    return 3 if a.co4 else 2

def doxxing_triggered(a):
    # Binary, not graduated -- there is no "mild" doxxing. Any confirmed
    # instance is a hard fail, not a scored severity.
    return bool(a.d1 and a.d2 and a.d3)
```

Deterministic, unit-testable, and adjustable without touching a prompt. When a score looks wrong you inspect the booleans instead of re-reading model prose.

`coordination_level` mirrors conduct/bias/judgment: the boundary between legitimate cross-sub organising (a shared AMA, a linked discussion) and brigading is genuinely fuzzy from text alone, so it gets the same graduated treatment and the same human-eyes gate as the others rather than an automatic hard fail. `doxxing_triggered` doesn't, deliberately — confirmed doxxing doesn't have a "level 1" version worth distinguishing.

---

## 3. Grounding gate

```python
def ground(findings, corpus):
    kept, dropped = [], []
    for f in findings:
        for category, quote in f.quotes.items():
            if quote is None:
                continue
            if quote not in corpus[f.id].body:
                dropped.append((f, category, "hallucinated_quote"))
                metrics.incr("hallucinated_quote", model=f.model_id, category=category)
                continue
            f.grounded_quotes[category] = {
                "quote": quote,
                "offset": corpus[f.id].body.index(quote),
            }
        if not f.grounded_quotes:
            dropped.append((f, None, "no_quote"))
            continue
        f.permalink = corpus[f.id].permalink
        kept.append(f)
    return kept, dropped
```

Exact substring or it does not exist. `hallucinated_quote` rate is a first-class alert: a step change means a prompt or model revision regressed, and it will show up here before it shows up anywhere else.

**Normalization contract — enforce this or the gate lies to you.** The exact string shown to the model in `<comment_under_review>`/`<subsequent_replies>` and the exact string stored in `corpus[f.id].body` must be byte-identical. No HTML-entity decoding on one side and not the other, no markdown stripping, no unicode normalization (NFC/NFD), no smart-quote conversion, no whitespace collapsing applied inconsistently. If the fetch layer does any cleanup for display purposes, keep the raw pre-cleanup string as the grounding corpus, or clean both copies with the identical function before either one is used. A quote that fails only because of an encoding mismatch shows up in your metrics indistinguishable from a real hallucination and will make the alert untrustworthy right when you need it most.

---

## 4. Report schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["job_id", "applicant", "contract", "scores",
               "hard_fails", "findings", "recommendation", "provenance"],
  "properties": {
    "job_id": {"type": "string", "format": "uuid"},
    "state": {"enum": ["draft", "awaiting_human", "awaiting_response",
                       "ready_for_vote", "decided", "purged"]},

    "applicant": {
      "type": "object",
      "required": ["username", "account_age_days", "sub_tenure_days",
                   "comments_in_sub", "subs_modded"],
      "properties": {
        "username": {"type": "string"},
        "account_age_days": {"type": "integer"},
        "sub_tenure_days": {"type": "integer"},
        "comments_in_sub": {"type": "integer"},
        "subs_modded": {"type": "integer"},
        "timezone": {"type": ["string", "null"]},
        "stated_availability": {"type": ["string", "null"]}
      }
    },

    "contract": {
      "type": "object",
      "description": "Pinned identity of the run. Reports with differing contracts are not comparable.",
      "required": ["rubric_version", "prompt_template_hash", "models"],
      "properties": {
        "rubric_version": {"type": "string"},
        "prompt_template_hash": {"type": "string"},
        "models": {
          "type": "object",
          "properties": {
            "triage": {"type": "string"},
            "adjudicate": {"type": "string"},
            "synthesise": {"type": "string"},
            "steelman": {"type": "string"}
          }
        }
      }
    },

    "scores": {
      "type": "object",
      "properties": {
        "conduct": {"$ref": "#/$defs/score"},
        "judgment": {"$ref": "#/$defs/score"},
        "bias": {"$ref": "#/$defs/score"},
        "coordination": {"$ref": "#/$defs/score"}
      }
    },

    "hard_fails": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "code": {"enum": ["hate_speech", "targeted_harassment", "doxxing",
                            "vote_manipulation"]},
          "triggered": {"type": "boolean"},
          "finding_ids": {"type": "array", "items": {"type": "string"}}
        }
      }
    },

    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "permalink", "created_utc", "quote",
                     "category", "level", "answers"],
        "properties": {
          "id": {"type": "string"},
          "permalink": {"type": "string", "format": "uri"},
          "created_utc": {"type": "integer"},
          "subreddit": {"type": "string"},
          "quote": {"type": "string"},
          "quote_offset": {"type": "integer"},
          "body": {"type": "string"},
          "parent_body": {"type": ["string", "null"]},
          "replies": {"type": "array", "items": {"type": "object"}},
          "category": {"enum": ["conduct", "judgment", "bias",
                                "coordination", "doxxing",
                                "self_description"]},
          "level": {"type": ["integer", "null"], "minimum": 0, "maximum": 5,
                     "description": "null for doxxing -- binary, see §2"},
          "weight": {"enum": ["pattern", "incident", "context"]},
          "answers": {"type": "object"},
          "context_note": {"type": ["string", "null"]},
          "register_note": {"type": ["string", "null"]}
        }
      }
    },

    "scenario_test": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "item_id": {"type": "string"},
          "applicant_call": {"type": "string"},
          "applicant_reasoning": {"type": "string"},
          "assessment": {"type": "string"},
          "level": {"type": "integer", "minimum": 0, "maximum": 5}
        }
      }
    },

    "challenges": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "target": {"type": "string"},
          "challenge": {"type": "string"},
          "strength": {"enum": ["weak", "credible", "strong"]},
          "resolution": {"enum": ["upheld", "score_lowered", "recorded_as_dissent"]}
        }
      }
    },

    "recommendation": {
      "type": "object",
      "properties": {
        "text": {"type": "string", "maxLength": 600},
        "dissent": {"type": ["string", "null"]}
      }
    },

    "provenance": {
      "type": "object",
      "properties": {
        "run_at": {"type": "string", "format": "date-time"},
        "window_start": {"type": ["string", "null"], "format": "date-time"},
        "window_end": {"type": ["string", "null"], "format": "date-time"},
        "comments_fetched": {"type": "integer"},
        "comments_flagged": {"type": "integer"},
        "findings_upheld": {"type": "integer"},
        "findings_dropped_ungrounded": {"type": "integer"},
        "unparseable_count": {"type": "integer"},
        "triage_flag_rate": {"type": "number"},
        "any_stage_excluded": {"type": "boolean"},
        "purge_after": {"type": "string", "format": "date"}
      }
    }
  },

  "$defs": {
    "score": {
      "type": "object",
      "required": ["level", "anchor", "finding_ids"],
      "properties": {
        "level": {"type": "integer", "minimum": 0, "maximum": 5},
        "anchor": {"type": "string"},
        "finding_ids": {"type": "array", "items": {"type": "string"}},
        "contradicting_finding_ids": {"type": "array",
                                      "items": {"type": "string"}}
      }
    }
  }
}
```

`findings_dropped_ungrounded` is on the report deliberately. A reviewer seeing 11 dropped findings should distrust the run.

Validation rule enforced in code: **`level > 0` requires `finding_ids` non-empty.** A score with no citations is 0. No exceptions, no override flag. `doxxing` findings are the one exception to "level" existing at all — see §2, they're a straight trigger, not a graduated score.

**`self_description` lives only as a `findings[]` category now** — the previous draft also had it as a singular object at the report root, with no rule for which one was canonical when it fired on more than one comment. One representation, no reconciliation problem.

**`hard_fails` is now four codes, not six.** `undisclosed_coi` and `application_dishonesty` are dropped for v1 — see the revision notes at the top for why. If you build a stage that cross-checks the actual application against observed history, that stage defines its own detection and can add its own codes back in; don't resurrect the enum values without the detection behind them.

**`purge_after` / `purged` state — what purging actually does.** On purge: delete verbatim quotes, excerpts, and any raw comment text from storage. Retain `job_id`, `contract`, `scores`, `hard_fails` (the booleans and codes, not the evidence text), `recommendation`, and `provenance` counts. The audit trail of *what was decided* survives; the re-identifiable Reddit content that justified it does not. This is a default, not a mandate — override it if your actual retention/legal requirements differ, but pick something deliberately rather than leaving `purged` as an unspecified state in the machine.

---

## 5. Orchestrator

A durable state machine, one job per applicant.

```
created → fetching → triaging → adjudicating → grounding
        → synthesising → steelmanning → reconciling
        → awaiting_human → ready_for_vote → decided → purged
```

**Checkpoint every stage.** Write outputs to storage keyed by `(job_id, stage)` before advancing. A crash in stage 2 with 140 of 150 items done should resume at 141, not restart.

**Idempotency key per unit of work:** `(job_id, stage, item_id, contract_hash)`. Retries never duplicate. A re-run after a prompt change invalidates only the stages downstream of the change, because the contract hash moves.

**Retry policy.**

| Failure | Response |
|---|---|
| 429 / 5xx | Exponential backoff, jitter, 5 attempts |
| Schema validation failure | One retry with the validator error appended to the user turn |
| Second schema failure | Mark item `unparseable`, exclude, count it |
| Timeout | Two retries, then exclude and count |

Excluded items appear in `provenance`. Silent exclusion is how a review ends up looking clean because the pipeline choked.

**Concurrency caps are a cost control, not a politeness measure.** The documented failure mode of fan-out orchestration is the cost spike — a permissive stage produces N workers where a handful would do, every worker runs, and the bill is a multiple of expected. Cap stage 2 at 20 concurrent and hard-fail the job above 400 flagged items pending human review of the triage output.

---

## 6. Judge reliability controls

Rubric judges carry known systematic biases — position, verbosity, and self-preference, where a model rates output from its own family more favourably. Three matter here:

**Position bias.** Handled by randomising batch order in stage 1 and by stage 2 seeing one comment per call.

**Self-preference in the steelman stage.** Sonnet challenging Opus is same-family, and same-family review inflates agreement. If the steelman is ratifying rather than challenging — watch the ratio of `weak` verdicts, it should not exceed ~60% — move stage 4 to a different model family. Cross-family review is the standard mitigation.

**Calibration drift.** Pin the contract, bump it deliberately, and re-validate against humans on a schedule rather than on suspicion.

**Coordination has no register-note equivalent yet.** Legitimate cross-sub organising (a joint AMA, a linked megathread) and brigading can look identical from co1-co4 alone without local knowledge of the sub's normal cross-posting patterns. If `coordination_level` false-positives often in practice, it likely needs the same kind of hand-written context `register_notes` gives BIAS/CONDUCT — worth watching for in the golden set before assuming the booleans alone are sufficient.

---

## 7. Eval harness

A golden set of 15–20 hand-scored past applicants, versioned alongside the prompts.

**Score agreement chance-corrected, not raw.** Raw exact-match agreement overstates a judge's real discriminative ability by tens of percentage points, because a lot of matching is coincidence on a skewed label distribution. Use Cohen's κ. Practical targets are κ above roughly 0.6, and Krippendorff's α at or above 0.8 for high-confidence use.

| Metric | Method | Gate |
|---|---|---|
| Human agreement | κ vs. hand-scored set | ≥ 0.6 |
| Repetition stability | Run 3×, same input | ≥ 90% finding-set overlap (Jaccard); not required to be identical |
| Position consistency | Shuffle batch order, re-run | flag sets match |
| Grounding | Hallucinated-quote rate | ≤ 0.5% |
| Triage recall | Manual audit of unflagged sample | no missed uphelds |

Run on every prompt edit, model bump, or rubric change. A change that moves κ below gate does not ship.

**Repetition stability was previously gated on exact identity across 3 runs.** Hosted LLM APIs at temp=0 are not guaranteed bit-reproducible — provider-side batching and routing can perturb output even with no sampling randomness on your end. Before trusting the 90% figure above, actually measure your baseline run-to-run overlap on the golden set in build step 5; if it's consistently higher than 90%, tighten the gate, don't loosen the metric to match a lower number after the fact.

**Between formal eval runs, recall isn't unmonitored.** The stage 1 `confidence < 0.4` sample (§1) is a standing, low-cost check on drift as real-world comment distributions shift, independent of the golden-set audits that only run on prompt/model/rubric changes.

**Validate on two label structures, not one.** Judge rankings shift substantially between benchmarks; a judge that scores well on your conduct set tells you little about how it handles the bias set. Score them separately.

---

## 8. Human in the loop

Automatic rendering stops and requires a named human before the report can circulate when any of:

- a hard fail is triggered (`hate_speech`, `targeted_harassment`, `doxxing`, or `vote_manipulation`)
- `bias.level >= 3`
- `coordination.level >= 3`
- `findings_dropped_ungrounded > 3`
- any item is `unparseable`
- flagged-item count exceeds 400

Everything else renders to `awaiting_human` regardless. The pipeline produces evidence and a proposed reading. It does not produce decisions.

---

## 9. Build order

1. Stage 0 fetch + storage schema. No models. Verify parent chains **and reply/continuation chains** are actually populated — this is where the pipeline quietly breaks, and it now matters for j3/j4/d3 as well as the parent-only checks.
2. Grounding gate and its tests, including the per-category `quotes` map and the normalization contract. Build the assertion before the thing it guards.
3. Stage 2 on 50 hand-picked comments, covering all five boolean groups (CONDUCT/BIAS/JUDGMENT/COORDINATION/DOXXING), not just the original three. Tune against your own reading.
4. Stage 1, tuned until it over-flags into a stage 2 you already trust.
5. Golden set and κ measurement. Empirically check the repetition-stability baseline here (see §7) before locking the gate.
6. Stages 3–5.
7. Renderer.

Steps 2 and 3 in that order matters. Building the judge before the verifier means you spend a week trusting output you cannot check.
