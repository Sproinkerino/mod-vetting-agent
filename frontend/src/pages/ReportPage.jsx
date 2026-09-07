import { useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useStore } from '../lib/mockStore';
import { groupFindingsById } from '../lib/findings';
import { isDegraded } from '../components/RunIntegrityStrip';
import RunIntegrityStrip from '../components/RunIntegrityStrip';
import HardFailChips from '../components/HardFailChips';
import ScoreMeters from '../components/ScoreMeters';
import FindingCard from '../components/FindingCard';
import ScenarioTest from '../components/ScenarioTest';
import Challenges from '../components/Challenges';
import Recommendation from '../components/Recommendation';
import GatePanel from '../components/GatePanel';
import VotePanel, { MOD_TEAM } from '../components/VotePanel';
import AuditLog from '../components/AuditLog';

function sortGroups(groups, sortBy) {
  const withDates = groups.map((g) => ({ ...g, date: Math.max(...g.categoryFindings.map((f) => f.created_utc)) }));
  if (sortBy === 'category') {
    return [...withDates].sort((a, b) => a.categoryFindings[0].category.localeCompare(b.categoryFindings[0].category));
  }
  return [...withDates].sort((a, b) => b.date - a.date); // FR-R6 default: newest first
}

export default function ReportPage() {
  const { jobId } = useParams();
  const { jobs, quorum, releaseForVote, sendBack, castVote } = useStore();
  const [sortBy, setSortBy] = useState('date');
  const [currentActor, setCurrentActor] = useState(MOD_TEAM[0]);

  const job = jobs.find((j) => j.id === jobId);

  const groups = useMemo(() => {
    if (!job?.report) return [];
    return sortGroups(groupFindingsById(job.report.findings), sortBy);
  }, [job, sortBy]);

  if (!job) {
    return (
      <div className="empty-state">
        <h1>Job not found</h1>
        <Link to="/">Back to queue</Link>
      </div>
    );
  }

  if (job.state === 'purged') {
    return (
      <div className="tombstone">
        <h1>u/{job.applicantUsername} — report purged</h1>
        <p>Purged at {new Date(job.purgedAt).toLocaleString()}.</p>
        <p>
          Per the retention policy, the evidence text was deleted; the decision record (scores,
          hard-fail codes, recommendation, and provenance counts) is retained.
        </p>
        <AuditLog entries={job.auditLog} />
        <Link to="/">Back to queue</Link>
      </div>
    );
  }

  if (job.state === 'running') {
    return (
      <div className="empty-state">
        <h1>u/{job.applicantUsername} — running</h1>
        <p>
          Stage: <strong>{job.stage}</strong> — {job.progress.completed} / {job.progress.total} items
        </p>
      </div>
    );
  }

  const report = job.report;
  const degraded = isDegraded(report);
  const blocked = report._human_gate.blocked;

  return (
    <div className="report-page">
      <div className="actor-bar no-print">
        <label>
          Acting as:{' '}
          <select value={currentActor} onChange={(e) => setCurrentActor(e.target.value)}>
            {MOD_TEAM.map((m) => (
              <option key={m}>{m}</option>
            ))}
          </select>
        </label>
        <Link to="/">← Queue</Link>
      </div>

      {/* FR-R1 order: header · integrity strip · context row · hard fails
          · scores · findings · scenario test · challenges ·
          recommendation · footer */}
      <header className="report-header">
        <h1>Applicant review: u/{report.applicant.username}</h1>
      </header>

      <RunIntegrityStrip report={report} />

      <section className="context-row">
        <span>Account age: {report.applicant.account_age_days}d</span>
        <span>Sub tenure: {report.applicant.sub_tenure_days}d</span>
        <span>Comments in sub: {report.applicant.comments_in_sub}</span>
        <span>Subs modded: {report.applicant.subs_modded}</span>
        {report.applicant.timezone && <span>TZ: {report.applicant.timezone}</span>}
        {report.applicant.stated_availability && <span>Availability: {report.applicant.stated_availability}</span>}
      </section>

      <HardFailChips hardFails={report.hard_fails} />

      {/* FR-I4: a degraded run suppresses all four score meters */}
      {!degraded && <ScoreMeters scores={report.scores} />}
      {degraded && (
        <p className="meters-suppressed no-print">Score meters suppressed — run is degraded, see integrity strip above.</p>
      )}

      <section className="findings-section">
        <div className="findings-section-header">
          <h2>Findings ({groups.length} comments, {report.findings.length} total)</h2>
          <div className="sort-controls no-print">
            <label>
              Sort:{' '}
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                <option value="date">Newest first</option>
                <option value="category">Category</option>
              </select>
            </label>
          </div>
        </div>

        {/* FR-S1: zero findings renders as a result, not an error */}
        {groups.length === 0 ? (
          <p className="no-findings-result">
            No findings in the window. {report.provenance.comments_fetched} comments fetched,{' '}
            {report.provenance.comments_flagged} flagged by triage — this is an empty result, not a
            failed fetch.
          </p>
        ) : (
          groups.map((g) => <FindingCard key={g.id} id={g.id} categoryFindings={g.categoryFindings} />)
        )}
      </section>

      <ScenarioTest items={report.scenario_test} />
      <Challenges challenges={report.challenges} />
      <Recommendation recommendation={report.recommendation} challenges={report.challenges} />

      {/* FR-G: only reachable for jobs holding on a gate condition */}
      {job.state === 'gated' && (
        <GatePanel
          job={job}
          onRelease={() => releaseForVote(job.id, currentActor)}
          onSendBack={(note) => sendBack(job.id, currentActor, note)}
        />
      )}

      {!blocked && job.state !== 'gated' && (
        <VotePanel job={job} quorum={quorum} currentActor={currentActor} onVote={(voter, choice, note) => castVote(job.id, voter, choice, note)} />
      )}

      <AuditLog entries={job.auditLog} />

      <footer className="report-footer">
        {/* FR-R7 */}
        <p>Purge date: {report.provenance.purge_after}</p>
        <p className="mono">
          Contract: {report.contract.rubric_version} / {report.contract.prompt_template_hash}
        </p>
      </footer>
    </div>
  );
}
