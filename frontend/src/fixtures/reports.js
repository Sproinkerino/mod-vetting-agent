// Report-level fixtures, matching schema/report.schema.json exactly (this
// is what the real pipeline's assemble_report() emits). All fabricated
// test data -- no real applicants.
import { judgmentWithReplies, multiCategory } from './findingCards';

const baseContract = {
  rubric_version: 'v1',
  prompt_template_hash: 'a1b2c3d4e5f6a7b8',
  models: { triage: 'claude-haiku-4-5-20251001', adjudicate: 'claude-sonnet-5' },
};

const baseApplicant = {
  username: 'fake_applicant_one',
  account_age_days: 820,
  sub_tenure_days: 340,
  comments_in_sub: 214,
  subs_modded: 2,
  timezone: 'America/Chicago',
  stated_availability: '10-15 hrs/week',
};

export const cleanReport = {
  job_id: 'job-clean-0001',
  state: 'awaiting_human',
  applicant: baseApplicant,
  contract: baseContract,
  scores: {
    conduct: { level: 1, anchor: 'isolated / responsive, not initiated', finding_ids: ['fx_multi'] },
    bias: { level: 2, anchor: 'confirmed, not aimed at an individual', finding_ids: ['fx_multi'] },
    judgment: { level: 4, anchor: 'confirmed and maintained after correction', finding_ids: ['fx_judgment'] },
    coordination: { level: 0, anchor: 'cleared', finding_ids: [] },
  },
  hard_fails: [
    { code: 'hate_speech', triggered: false, finding_ids: [] },
    { code: 'targeted_harassment', triggered: false, finding_ids: [] },
    { code: 'doxxing', triggered: false, finding_ids: [] },
    { code: 'vote_manipulation', triggered: false, finding_ids: [] },
  ],
  findings: [...multiCategory, ...judgmentWithReplies],
  scenario_test: [
    {
      item_id: 'sc1',
      applicant_call: 'Remove and warn',
      applicant_reasoning: 'Post directly violates rule 3 on self-promotion.',
      assessment: 'Consistent with how the team has handled similar cases.',
      level: 1,
    },
  ],
  challenges: [
    {
      target: 'conduct.level',
      challenge: "The 'responding, not initiating' comment could be read as still within the sub's normal debate register.",
      strength: 'weak',
      resolution: 'upheld',
    },
  ],
  recommendation: {
    text: 'Not generated -- stages 3-5 (synthesise/steelman/reconcile) are not implemented in this build. This report contains evidence and computed scores only; see findings and scores for a human to read directly.',
    dissent: null,
  },
  provenance: {
    run_at: '2026-08-30T14:02:11Z',
    window_start: '2025-08-01T00:00:00Z',
    window_end: '2026-08-30T00:00:00Z',
    comments_fetched: 214,
    comments_flagged: 9,
    findings_upheld: 3,
    findings_dropped_ungrounded: 0,
    unparseable_count: 0,
    triage_flag_rate: 0.11,
    any_stage_excluded: false,
    purge_after: '2026-11-28',
  },
  _human_gate: { blocked: false, reasons: [] },
};

export const degradedReport = {
  ...cleanReport,
  job_id: 'job-degraded-0002',
  applicant: { ...baseApplicant, username: 'fake_applicant_two' },
  provenance: {
    ...cleanReport.provenance,
    findings_dropped_ungrounded: 4,
    unparseable_count: 1,
  },
  _human_gate: {
    blocked: true,
    reasons: ['findings_dropped_ungrounded (4) > 3', 'one or more items unparseable'],
  },
};

export const gatedReport = {
  ...cleanReport,
  job_id: 'job-gated-0003',
  applicant: { ...baseApplicant, username: 'fake_applicant_three' },
  hard_fails: [
    { code: 'hate_speech', triggered: false, finding_ids: [] },
    { code: 'targeted_harassment', triggered: true, finding_ids: ['fx_multi'] },
    { code: 'doxxing', triggered: false, finding_ids: [] },
    { code: 'vote_manipulation', triggered: false, finding_ids: [] },
  ],
  _human_gate: { blocked: true, reasons: ['hard fail triggered: targeted_harassment'] },
};

export const zeroFindingsReport = {
  ...cleanReport,
  job_id: 'job-zero-0004',
  applicant: { ...baseApplicant, username: 'fake_applicant_four' },
  scores: {
    conduct: { level: 0, anchor: 'cleared', finding_ids: [] },
    bias: { level: 0, anchor: 'cleared', finding_ids: [] },
    judgment: { level: 0, anchor: 'cleared', finding_ids: [] },
    coordination: { level: 0, anchor: 'cleared', finding_ids: [] },
  },
  hard_fails: cleanReport.hard_fails.map((hf) => ({ ...hf, triggered: false })),
  findings: [],
  provenance: {
    ...cleanReport.provenance,
    comments_fetched: 88,
    comments_flagged: 0,
    findings_upheld: 0,
  },
  _human_gate: { blocked: false, reasons: [] },
};

export const runningJob = {
  id: 'job-running-0005',
  applicantUsername: 'fake_applicant_five',
  stage: 'adjudicating',
  progress: { completed: 12, total: 20 },
};

export const purgedJob = {
  id: 'job-purged-0006',
  applicantUsername: 'fake_applicant_six',
  purgedAt: '2026-06-01T09:00:00Z',
  auditLog: [
    { action: 'gate_release', actor: 'mod_bob', at: '2026-02-01T10:00:00Z' },
    { action: 'vote', actor: 'mod_alice', choice: 'approve', at: '2026-02-02T10:00:00Z' },
    { action: 'vote', actor: 'mod_bob', choice: 'approve', at: '2026-02-02T11:00:00Z' },
    { action: 'vote', actor: 'mod_carol', choice: 'decline', note: 'Concerned about tenure.', at: '2026-02-02T12:00:00Z' },
    { action: 'purge', actor: 'head_mod_dana', at: '2026-06-01T09:00:00Z' },
  ],
};
