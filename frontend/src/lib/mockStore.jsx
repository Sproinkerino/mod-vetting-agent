// Queue position, votes, gate actions, and the audit log are NOT part of
// report.json (see schema/report.schema.json) -- they're application
// state a real backend API would own. This is a local, in-memory stand-in
// so the queue/gate/vote/audit surfaces (FR-Q/FR-G/FR-V/FR-A) are
// demonstrable against the fixtures before that API exists. Swap this
// module for real API calls; the component props/contract stay the same.

import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import {
  cleanReport,
  degradedReport,
  gatedReport,
  runningJob,
  zeroFindingsReport,
  purgedJob,
} from '../fixtures/reports';

const QUORUM = 3;

function makeInitialJobs() {
  return [
    {
      id: cleanReport.job_id,
      applicantUsername: cleanReport.applicant.username,
      state: 'ready_for_vote',
      report: cleanReport,
      auditLog: [],
      votes: [{ voter: 'mod_alice', choice: 'approve', note: null }],
    },
    {
      id: degradedReport.job_id,
      applicantUsername: degradedReport.applicant.username,
      state: 'gated',
      report: degradedReport,
      auditLog: [],
      votes: [],
    },
    {
      id: gatedReport.job_id,
      applicantUsername: gatedReport.applicant.username,
      state: 'gated',
      report: gatedReport,
      auditLog: [],
      votes: [],
    },
    {
      id: zeroFindingsReport.job_id,
      applicantUsername: zeroFindingsReport.applicant.username,
      state: 'ready_for_vote',
      report: zeroFindingsReport,
      auditLog: [],
      votes: [],
    },
    {
      id: runningJob.id,
      applicantUsername: runningJob.applicantUsername,
      state: 'running',
      report: null,
      stage: runningJob.stage,
      progress: runningJob.progress,
      auditLog: [],
      votes: [],
    },
    {
      id: purgedJob.id,
      applicantUsername: purgedJob.applicantUsername,
      state: 'purged',
      report: null,
      purgedAt: purgedJob.purgedAt,
      auditLog: purgedJob.auditLog,
      votes: [],
    },
  ];
}

const StoreContext = createContext(null);

export function StoreProvider({ children }) {
  const [jobs, setJobs] = useState(makeInitialJobs);

  const appendAudit = useCallback((jobId, entry) => {
    setJobs((prev) =>
      prev.map((j) =>
        j.id === jobId
          ? { ...j, auditLog: [...j.auditLog, { ...entry, at: new Date().toISOString() }] }
          : j
      )
    );
  }, []);

  const releaseForVote = useCallback(
    (jobId, actor) => {
      setJobs((prev) => prev.map((j) => (j.id === jobId ? { ...j, state: 'ready_for_vote' } : j)));
      appendAudit(jobId, { action: 'gate_release', actor });
    },
    [appendAudit]
  );

  const sendBack = useCallback(
    (jobId, actor, note) => {
      if (!note || note.length < 20) throw new Error('Send back requires a note of at least 20 characters.');
      setJobs((prev) => prev.map((j) => (j.id === jobId ? { ...j, state: 'sent_back' } : j)));
      appendAudit(jobId, { action: 'gate_send_back', actor, note });
    },
    [appendAudit]
  );

  const castVote = useCallback(
    (jobId, voter, choice, note) => {
      if (choice === 'decline' && !note) throw new Error('Decline requires a note.');
      setJobs((prev) =>
        prev.map((j) => {
          if (j.id !== jobId) return j;
          const votes = [...j.votes.filter((v) => v.voter !== voter), { voter, choice, note: note || null }];
          const decided = votes.length >= QUORUM;
          return { ...j, votes, state: decided ? 'decided' : j.state };
        })
      );
      appendAudit(jobId, { action: 'vote', actor: voter, choice, note });
    },
    [appendAudit]
  );

  const resumeJob = useCallback(
    (jobId, actor) => {
      setJobs((prev) => prev.map((j) => (j.id === jobId ? { ...j, state: 'running' } : j)));
      appendAudit(jobId, { action: 'manual_resume', actor, note: 'Resumed from last checkpoint' });
    },
    [appendAudit]
  );

  const purgeJob = useCallback(
    (jobId, actor) => {
      setJobs((prev) =>
        prev.map((j) => (j.id === jobId ? { ...j, state: 'purged', report: null, purgedAt: new Date().toISOString() } : j))
      );
      appendAudit(jobId, { action: 'purge', actor });
    },
    [appendAudit]
  );

  const value = useMemo(
    () => ({ jobs, quorum: QUORUM, releaseForVote, sendBack, castVote, resumeJob, purgeJob }),
    [jobs, releaseForVote, sendBack, castVote, resumeJob, purgeJob]
  );

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore() {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error('useStore must be used within StoreProvider');
  return ctx;
}
