# Applicant review — single-report tool

Redesigned from the original queue/gate/vote frontend (see git history /
`frontend-prd.md` for that version) per direct feedback: "design is all
wrong... a tool where you can input a username then a single report comes
out. No queue etc. Easier to read report."

## What it is

One input field. Type a Reddit username, click "Generate report," wait
(a real run takes a couple of minutes — dozens of concurrency-capped LLM
calls), read the report. No queue, no gate, no vote, no audit log, no
mock store. Talks directly to the deployed API
(`https://mod-vetting-api.onrender.com`, see `src/lib/api.js`).

**This produces a real evidence document about a real, identifiable
person.** Only enter an actual applicant under actual consideration.

## What changed from the PRD version

- Removed: Queue, Gate, Vote, Audit log, and the local mock store that
  backed them (`lib/mockStore.jsx` — deleted; votes/queue-state/audit
  trail aren't part of `report.json` and need a real backend API this
  project doesn't have).
- Removed: the per-finding boolean grid (c1-c5, b1-b4, j1-j4, etc.) —
  explicitly dropped per feedback, not just collapsed. A finding now
  shows category + level + the cited quote highlighted in its full
  context, nothing else. (`lib/findings.js`'s `BOOLEAN_GROUPS`/
  `CLEARING_CRITERIA` and the `CategoryBlock`/`BooleanPill` components
  that rendered them are gone.)
- Removed the react-router-dom dependency — there's only one screen now
  (search, or report), no routes to manage.
- Kept: the quote-offset integrity check (a citation that doesn't
  actually appear in the comment body renders as an error with its level
  withheld, never a fabricated highlight), the degraded-run banner, hard
  fail chips (still only the 4 real codes), and score meters (still
  level+anchor verbatim, no color-scale, no composite score).

## Known limitation

`api.py`'s job tracking is an in-memory dict in the API process. It does
NOT survive a Render redeploy or restart, and if the service ever runs
more than one instance, a request can land on an instance that never saw
the job. Confirmed this actually happens during a deploy window while
testing this build (a job started right as a push triggered a redeploy
404'd on the next poll; retried a minute later once the deploy settled
and it worked cleanly end to end). Fine for a single always-on instance
between deploys; not durable enough to promise a report survives a
production incident. Real fix would be to have `GET /jobs/{id}` fall back
to the SQLite storage layer (already durable, already checkpointed) — not
done in this pass.

## Running it

```bash
npm install
npm run dev
npm run build
```
