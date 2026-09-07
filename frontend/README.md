# Applicant review frontend

Implements `frontend-prd.md` (the PRD) against fixtures,
per its own M1 milestone: "M1 lands against hand-written fixtures before
stage 0 delivers anything real."

**No `mod-vetting-frontend-plan.md` (the referenced design doc) was
available to build against.** `src/index.css` is this build's own
reasonable defaults instead — evidence-first, no color-coded verdicts, AA
contrast, print-first — consistent with the PRD's stated principles, but
not a real design system. Swap freely.

## What's implemented

- **M1** — Finding card + fixtures. All 6 required fixture cases
  (`src/fixtures/findingCards.js`): mixed true/false/unknown booleans,
  multi-category (one comment id, two category tags), top-level comment,
  judgment finding with replies, and a deliberately corrupted offset that
  correctly suppresses its level and shows the integrity error (FR-C4).
- **M2** — Report route + print CSS (`@media print` in `index.css`, A4/Letter
  via `@page`, `break-inside: avoid` on finding cards, queue/gate/vote
  hidden via `.no-print`, permalinks print as visible URLs).
- **M3** — Integrity strip + degraded state (`RunIntegrityStrip.jsx`):
  meters suppressed and vote blocked when `findings_dropped_ungrounded >
  3`, any unparseable item, triage flag rate below 2%, or any stage
  excluded items.
- **M4** — Queue, grouped by state with the required per-row info.
- **M5** — Gate + vote + audit log, wired to a local mock store (see
  below) — full path from gate release through quorum, logged.
- **M6** (calibration workbench) — out of scope, PRD marks it V2.

## A real gap this build found and fixed in the *backend*

Building against the PRD's own acceptance criteria (FR-C2–C4: highlight
the quote inside the full comment body at `quote_offset`) surfaced that
`report.json`'s `findings[]` never actually carried the full comment
`body`, `parent_body`, or `replies` — only the isolated `quote`. An
offset into a body the frontend never receives is unusable. Fixed in the
backend (`../mod_vetting/report.py`, `stage2_adjudicate.py`,
`orchestrator.py`) and the schema, before this frontend was built against
it — see `../README.md` and `../implementation-spec.md`'s revision notes.

Also found: the first pass of `findingCards.js` had every "should be
valid" fixture's `quote_offset` hand-typed and **wrong** — verified with
a throwaway script before catching it. Fixed by computing offsets via
`body.indexOf(quote)` at load time instead of hand-typing them, so this
class of mistake can't recur silently.

## What's mocked, and why

`votes`, `queue state`, and the `audit log` are **not** part of
`report.json` (see `schema/report.schema.json`) — they're application
state a real backend API would own, which doesn't exist yet for this
pipeline (it currently only produces one `report.json` per run, no
gate/vote/audit endpoints). `src/lib/mockStore.js` is a local, in-memory
stand-in so M4/M5 are demonstrable against the fixtures; swap it for real
API calls when that backend exists. The frontend itself still never
computes/derives a *report* value (PRD §1 "Never") — grouping findings by
comment id and validating an offset are display bookkeeping and an
integrity check, not new derived scores.

## Running it

```bash
npm install
npm run dev    # http://localhost:5173 (or next free port)
npm run build
```
