# PRD — Applicant Review Frontend

**Status:** Draft for build
**Consumes:** `report.json` per the schema in `implementation-spec.md`
**Design direction:** `mod-vetting-frontend-plan.md` — tokens, type, wireframes, rationale
**This document:** requirements and acceptance criteria

---

## 1. Scope

### In, V1
Queue · report · finding card · run-integrity strip · gate · vote · print · audit log.

### Out, V1
Calibration workbench · QA tray · applicant-facing anything · editing findings by hand · re-running stages from the UI · notifications.

### Never
The frontend does not compute, derive, adjust, or infer any value that appears in `report.json`. It renders. Two surfaces computing the same score independently is how they end up disagreeing, and the score of record must be the one the pipeline stamped with a contract hash.

---

## 2. Users

| Role | Job |
|---|---|
| Reviewer | Clear gates, send bad runs back |
| Voter | Read a report, reach a defensible position, vote |
| Head mod | See what's blocked, manage retention |

All three are the same five people wearing different hats. No role-switching UI; permissions are per-action, not per-account.

---

## 3. Data contract

The report now carries **four scores** — `conduct`, `judgment`, `bias`, `coordination` — following the dev agent's addition of `coordination_level()`. `doxxing_triggered()` is binary and surfaces as a hard-fail chip, not a meter.

**Hard-fail chips are four, not six:** `hate_speech`, `targeted_harassment`, `doxxing`, `vote_manipulation`. `undisclosed_coi` and `application_dishonesty` were dropped as unservable by this pipeline. The UI must not render placeholder chips for them — an unfireable check displayed as "clear" is a false assurance, which is worse than its absence.

`self_description` is a finding category, not a root object. It renders as a finding card like any other, with `relevance` shown when present.

---

## 4. Functional requirements

### FR-C — Finding card

**FR-C1** Every boolean renders in one of three states: true, false, unknown. Unknown uses `unknown` hue plus the `—` glyph. Unknown is never rendered as blank, as false, or as a faded false.
**FR-C2** The parent comment renders expanded on first paint. No toggle, no truncation, no "show context" affordance. Where `parent_body` is null, the card states the comment is top-level.
**FR-C3** The quoted span renders highlighted inside the full comment body at `quote_offset`.
**FR-C4** Before highlighting, the renderer asserts `body.substr(offset, quote.length) === quote`. On mismatch it renders the card in an error state, shows the body unhighlighted, and does not display the derived level. A misplaced highlight is a fabricated accusation with a different mechanism.
**FR-C5** Findings sharing a `source comment id` render as one card with multiple category tags. Never one card per category.
**FR-C6** Each category on a card shows its booleans, its computed level or `cleared`, and the criterion that cleared it.
**FR-C7** The subsequent-replies block renders only when the card carries a judgment finding. Absent otherwise.
**FR-C8** `register_note` and `context_note` render when present, visually distinct from the pipeline's booleans.
**FR-C9** Permalink opens in a new tab. Present on every card without exception.

*Acceptance:* fixture set covers all three boolean states, a multi-category comment, a top-level comment, a judgment finding with replies, and a deliberately corrupted offset. All six render correctly and the corrupted one suppresses its level.

### FR-I — Run integrity

**FR-I1** The strip renders above all report content: window, fetched, flagged, findings, distinct comments, dropped ungrounded, unparseable, rubric version, contract hash.
**FR-I2** Headline finding count is **distinct source comments**, with total findings secondary.
**FR-I3** A run is degraded when any of: `findings_dropped_ungrounded > 3`, `unparseable > 0`, triage flag rate below floor, any stage excluded items.
**FR-I4** A degraded run renders the strip as a `flag` banner naming each condition, **suppresses all four score meters**, and blocks the vote action until a reviewer clears it at the gate.

*Acceptance:* a report with 4 dropped findings shows no meters and no vote button.

### FR-R — Report

**FR-R1** Order: header · integrity strip · context row · hard fails · scores · findings · scenario test · challenges · recommendation · footer.
**FR-R2** Meters render `level` and `anchor` verbatim from JSON. No colour scale, no red/amber/green, no composite or overall score anywhere.
**FR-R3** Any score with `level > 0` renders its `finding_ids` as links to the cards on the page. A score whose `finding_ids` is empty renders as an error, not as a score.
**FR-R4** `contradicting_finding_ids` render alongside the score they cut against, at equal visual weight.
**FR-R5** Challenges render with `strength` and `resolution`. Any challenge resolved `recorded_as_dissent` also renders in the recommendation block.
**FR-R6** Findings default to newest first; sortable by date and by category.
**FR-R7** The footer shows the purge date.

### FR-Q — Queue

**FR-Q1** Grouped by state, ordered: needs you · ready to vote · running · decided.
**FR-Q2** Running jobs show the current stage name and item progress. No indeterminate spinner.
**FR-Q3** Ready-to-vote rows show vote tally against quorum.
**FR-Q4** Decided rows show the purge countdown in days.
**FR-Q5** Failed jobs show the failing stage and a `Resume` action. Resume restarts from the last checkpoint, never from the beginning.

### FR-G — Gate

**FR-G1** The gate is reachable only for jobs holding on a gate condition.
**FR-G2** It names every condition that fired and links the findings behind each.
**FR-G3** Two actions only: `Release for vote` and `Send back`. `Send back` requires a note of at least 20 characters.
**FR-G4** No word on this screen approves, rejects, accepts, or declines an applicant. The gate acts on the report.
**FR-G5** The releasing user is recorded by name on the report and in the audit log.

### FR-V — Vote

**FR-V1** Vote is unavailable while a job is degraded, gated, or below `ready_for_vote`.
**FR-V2** Options: approve · decline · abstain, each with an optional note. Decline requires a note.
**FR-V3** Voters see the tally but not others' notes until they have voted. Reading a colleague's reasoning first is how five independent judgments become one.
**FR-V4** A vote is changeable until quorum is reached, then locked.
**FR-V5** On quorum the job moves to `decided` and the retention clock starts.

### FR-P — Print

**FR-P1** The report prints to A4 and Letter.
**FR-P2** Finding cards never split across a page break.
**FR-P3** Boolean states survive greyscale — glyph carries the state, colour reinforces it.
**FR-P4** Permalinks print as visible URLs.
**FR-P5** Queue, gate, and vote surfaces are `display: none` in print.

### FR-A — Audit

**FR-A1** Recorded with actor and timestamp: gate release, send-back with note, every vote and change, purge execution, manual resume.
**FR-A2** The log is append-only and visible on the report.
**FR-A3** Purge is irreversible and removes what the spec's purge definition says it removes, retaining only what that definition retains. The UI states both before confirming.

### FR-S — States

**FR-S1** Zero findings renders as a result, not an error: "No findings in the window," with fetch counts so an empty result is distinguishable from a broken fetch.
**FR-S2** Stage failure names the stage and the error.
**FR-S3** Purged jobs render a tombstone.
**FR-S4** No empty state anywhere is a bare illustration or a shrug. Each names what happened and what to do.

---

## 5. Non-functional

**Performance.** Report interactive under 1.5s on a mid-range laptop with 60 findings. Findings virtualise above 100 cards.
**Accessibility.** AA contrast. Full keyboard path to gate and vote actions with visible focus. Boolean state never encoded by colour alone. Reduced motion respected. Cards are semantic `<article>` elements with the parent as a `<blockquote>`, so a screen reader reaches the context before the verdict — same reason as the visual rule.
**Permissions.** Mod team only. No applicant access in V1. Gate and vote actions are per-user permissioned and enforced server-side, not by hiding buttons.
**Browsers.** Current Chrome, Firefox, Safari. No IE, no polyfill budget.

---

## 6. Telemetry

Three questions, and they are about whether the design worked, not about engagement:

1. **What fraction of voters expanded at least one finding before voting?** If this is low, the report is being treated as a verdict and the evidence-first design has failed.
2. Time from `ready_for_vote` to quorum.
3. Gate turnaround, and send-back rate by condition — a condition that never sends anything back is miscalibrated.

No per-user surveillance. Aggregate only.

---

## 7. Milestones

| # | Deliverable | Done when |
|---|---|---|
| M1 | Finding card + fixtures | All six fixture cases render; corrupted-offset case suppresses level |
| M2 | Report route + print | Prints clean on A4 and Letter, no split cards |
| M3 | Integrity strip + degraded state | 4-dropped report suppresses meters and blocks vote |
| M4 | Queue | All five states render with correct actions |
| M5 | Gate + vote + audit | Full path from gate release to quorum, logged |
| M6 | Calibration workbench | V2 |

M1 lands against hand-written fixtures before stage 0 delivers anything real. The fixtures are the renderer's test set for the life of the project.

---

## 8. Open questions

1. **Do mods vote from phones?** The report is designed print-first as a one-pager, and Reddit mod teams largely live on mobile. If voting happens on a phone, the finding card needs a mobile layout that keeps the parent comment visible above the fold, and that constraint should shape M1 rather than get retrofitted at M4.
2. Quorum size, and what happens on a tie.
3. Does a declined applicant get the reason, and at what specificity?
4. Can a voter see the report after purge, or does the tombstone stand alone?
5. Who holds purge permission — any mod, or head mod only?
6. Is there a reapplication path, and does it show the prior decision?
