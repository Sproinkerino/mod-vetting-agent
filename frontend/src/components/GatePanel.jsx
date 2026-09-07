import { useState } from 'react';

// FR-G1-G5. Only reachable for jobs holding on a gate condition.
export default function GatePanel({ job, onRelease, onSendBack }) {
  const [note, setNote] = useState('');
  const [error, setError] = useState(null);

  const reasons = job.report?._human_gate?.reasons || [];

  function handleSendBack() {
    try {
      onSendBack(note);
      setNote('');
      setError(null);
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <section className="gate-panel no-print">
      <h2>Gate</h2>
      {/* FR-G4: no word here approves, rejects, accepts, or declines an
          applicant -- the gate acts on the report. */}
      <p className="gate-intro">This gate reviews the RUN, not the applicant. Clear it to allow voting, or send the run back.</p>
      <ul className="gate-conditions">
        {reasons.map((r) => (
          <li key={r}>{r}</li>
        ))}
      </ul>
      <div className="gate-actions">
        <button type="button" className="btn btn-primary" onClick={onRelease}>
          Release for vote
        </button>
        <div className="gate-send-back">
          <textarea
            placeholder="Note (minimum 20 characters) explaining why this run is being sent back..."
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={3}
          />
          <button type="button" className="btn btn-secondary" onClick={handleSendBack}>
            Send back
          </button>
        </div>
        {error && <p className="gate-error">{error}</p>}
      </div>
    </section>
  );
}
