import { useState } from 'react';

const MOD_TEAM = ['mod_alice', 'mod_bob', 'mod_carol', 'mod_dave', 'head_mod_dana'];

// FR-V1-V5.
export default function VotePanel({ job, quorum, currentActor, onVote }) {
  const [choice, setChoice] = useState('approve');
  const [note, setNote] = useState('');
  const [error, setError] = useState(null);

  const eligible = job.state === 'ready_for_vote';
  const myVote = job.votes.find((v) => v.voter === currentActor);
  const locked = job.votes.length >= quorum;

  if (!eligible) {
    return (
      <section className="vote-panel no-print vote-unavailable">
        <h2>Vote</h2>
        <p>
          Voting is unavailable — this run is {job.state === 'gated' ? 'gated' : job.state === 'running' ? 'still running' : job.state}.
        </p>
      </section>
    );
  }

  function submit() {
    try {
      onVote(currentActor, choice, note || null);
      setError(null);
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <section className="vote-panel no-print">
      <h2>Vote</h2>
      {/* FR-V3: voters see the tally but not others' notes until they
          have voted */}
      <p className="vote-tally">
        {job.votes.length} / {quorum} votes cast
        {job.votes.map((v) => (myVote ? ` · ${v.voter}: ${v.choice}` : '')).join('')}
      </p>

      {myVote && !locked && <p className="vote-your-vote">Your vote: {myVote.choice} (changeable until quorum)</p>}

      {locked ? (
        <p className="vote-locked">Quorum reached — voting is locked.</p>
      ) : (
        <div className="vote-form">
          <div className="vote-choices">
            {['approve', 'decline', 'abstain'].map((c) => (
              <label key={c}>
                <input type="radio" name="vote-choice" value={c} checked={choice === c} onChange={() => setChoice(c)} />
                {c}
              </label>
            ))}
          </div>
          <textarea
            placeholder={choice === 'decline' ? 'Note (required for decline)' : 'Note (optional)'}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
          />
          <button type="button" className="btn btn-primary" onClick={submit}>
            {myVote ? 'Change vote' : 'Cast vote'}
          </button>
          {error && <p className="vote-error">{error}</p>}
        </div>
      )}
    </section>
  );
}

export { MOD_TEAM };
