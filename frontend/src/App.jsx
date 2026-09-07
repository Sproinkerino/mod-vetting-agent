import { useState } from 'react';
import { startJob, waitForJob } from './lib/api';
import { groupFindingsById } from './lib/findings';
import RunIntegrityStrip from './components/RunIntegrityStrip';
import HardFailChips from './components/HardFailChips';
import ScoreMeters from './components/ScoreMeters';
import FindingCard from './components/FindingCard';

const USERNAME_RE = /^[A-Za-z0-9_-]{3,20}$/;

export default function App() {
  const [username, setUsername] = useState('');
  const [stage, setStage] = useState('idle'); // idle | running | done | error
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [elapsedMs, setElapsedMs] = useState(0);

  async function handleSubmit(e) {
    e.preventDefault();
    const trimmed = username.trim();
    if (!USERNAME_RE.test(trimmed)) {
      setError('Enter a valid Reddit username (3-20 characters, letters/numbers/_/-, no u/ prefix).');
      setStage('error');
      return;
    }

    setStage('running');
    setError(null);
    setReport(null);
    setElapsedMs(0);

    try {
      const { job_id } = await startJob(trimmed);
      const result = await waitForJob(job_id, {
        onTick: (_entry, ms) => setElapsedMs(ms),
      });
      if (result.status === 'error') {
        setError(result.error || 'The pipeline failed.');
        setStage('error');
        return;
      }
      setReport(result.report);
      setStage('done');
    } catch (err) {
      setError(err.message);
      setStage('error');
    }
  }

  function reset() {
    setStage('idle');
    setReport(null);
    setError(null);
    setUsername('');
  }

  return (
    <div className="app-shell">
      {stage !== 'done' ? (
        <div className="search-view">
          <h1>Moderator applicant review</h1>
          <p className="search-intro">
            Enter a Reddit username to pull their public history and generate a cited findings
            report. This produces a real evidence document about a real person — only use it for
            an actual applicant under actual consideration.
          </p>
          <form onSubmit={handleSubmit} className="search-form">
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="username (no u/ prefix)"
              disabled={stage === 'running'}
              autoFocus
            />
            <button type="submit" className="btn btn-primary" disabled={stage === 'running'}>
              {stage === 'running' ? 'Running…' : 'Generate report'}
            </button>
          </form>

          {stage === 'running' && (
            <p className="running-status">
              Fetching history, triaging, and adjudicating — this takes a couple of minutes.{' '}
              {Math.round(elapsedMs / 1000)}s elapsed.
            </p>
          )}
          {stage === 'error' && <p className="search-error">{error}</p>}
        </div>
      ) : (
        <ReportView report={report} onNewSearch={reset} />
      )}
    </div>
  );
}

function ReportView({ report, onNewSearch }) {
  const groups = groupFindingsById(report.findings).sort(
    (a, b) => Math.max(...b.categoryFindings.map((f) => f.created_utc)) - Math.max(...a.categoryFindings.map((f) => f.created_utc))
  );

  return (
    <div className="report-view">
      <div className="report-top-bar">
        <button type="button" className="btn btn-secondary" onClick={onNewSearch}>
          ← New search
        </button>
      </div>

      <header className="report-header">
        <h1>u/{report.applicant.username}</h1>
      </header>

      <RunIntegrityStrip report={report} />
      <HardFailChips hardFails={report.hard_fails} />
      <ScoreMeters scores={report.scores} />

      <section className="findings-section">
        <h2>Findings ({groups.length})</h2>
        {groups.length === 0 ? (
          <p className="no-findings-result">
            No findings. {report.provenance.comments_fetched} comments checked,{' '}
            {report.provenance.comments_flagged} flagged for review — nothing held up under
            adjudication and grounding.
          </p>
        ) : (
          groups.map((g) => <FindingCard key={g.id} id={g.id} categoryFindings={g.categoryFindings} />)
        )}
      </section>

      <footer className="report-footer">
        <p>Purge date: {report.provenance.purge_after}</p>
        <p className="mono">
          Contract: {report.contract.rubric_version} / {report.contract.prompt_template_hash}
        </p>
      </footer>
    </div>
  );
}
