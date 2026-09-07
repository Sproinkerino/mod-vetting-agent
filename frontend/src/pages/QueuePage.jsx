import { Link } from 'react-router-dom';
import { useStore } from '../lib/mockStore';

// FR-Q1: grouped by state, ordered: needs you (gated + sent_back) · ready
// to vote · running · decided.
const GROUPS = [
  { key: 'needs_you', label: 'Needs you', match: (j) => j.state === 'gated' || j.state === 'sent_back' },
  { key: 'ready', label: 'Ready to vote', match: (j) => j.state === 'ready_for_vote' },
  { key: 'running', label: 'Running', match: (j) => j.state === 'running' },
  { key: 'decided', label: 'Decided', match: (j) => j.state === 'decided' },
];

function purgeCountdown(purgeAfter) {
  const days = Math.ceil((new Date(purgeAfter) - new Date()) / 86400000);
  return days > 0 ? `${days}d to purge` : 'purge overdue';
}

export default function QueuePage() {
  const { jobs, quorum, resumeJob } = useStore();

  return (
    <div className="queue-page">
      <h1>Applicant review queue</h1>
      {GROUPS.map((group) => {
        const groupJobs = jobs.filter(group.match);
        return (
          <section key={group.key} className="queue-group">
            <h2>
              {group.label} <span className="queue-count">({groupJobs.length})</span>
            </h2>
            {groupJobs.length === 0 ? (
              <p className="queue-empty">Nothing here.</p>
            ) : (
              <ul className="queue-list">
                {groupJobs.map((j) => (
                  <li key={j.id} className="queue-row">
                    <Link to={`/report/${j.id}`} className="queue-applicant">
                      u/{j.applicantUsername}
                    </Link>

                    {/* FR-Q2: running jobs show current stage + item
                        progress, no indeterminate spinner */}
                    {j.state === 'running' && (
                      <span className="queue-progress">
                        {j.stage} — {j.progress.completed}/{j.progress.total}
                      </span>
                    )}

                    {/* FR-Q3: ready-to-vote rows show vote tally against quorum */}
                    {j.state === 'ready_for_vote' && (
                      <span className="queue-tally">
                        {j.votes.length}/{quorum} votes
                      </span>
                    )}

                    {(j.state === 'gated' || j.state === 'sent_back') && j.report && (
                      <span className="queue-gate-reasons">{j.report._human_gate.reasons.join('; ')}</span>
                    )}

                    {/* FR-Q4: decided rows show purge countdown in days */}
                    {j.state === 'decided' && j.report && (
                      <span className="queue-purge-countdown">{purgeCountdown(j.report.provenance.purge_after)}</span>
                    )}

                    {/* FR-Q5: failed jobs show failing stage + Resume
                        action, which restarts from the last checkpoint,
                        never from the beginning */}
                    {j.state === 'failed' && (
                      <button type="button" className="btn btn-secondary" onClick={() => resumeJob(j.id, 'head_mod_dana')}>
                        Resume from checkpoint
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>
        );
      })}
    </div>
  );
}
