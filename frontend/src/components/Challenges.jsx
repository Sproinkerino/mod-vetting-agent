// FR-R5: challenges render with strength and resolution. Any challenge
// resolved recorded_as_dissent also renders in the recommendation block
// (handled by the parent ReportPage passing dissentChallenges down).
export default function Challenges({ challenges }) {
  if (!challenges || challenges.length === 0) return null;
  return (
    <section className="challenges">
      <h2>Challenges</h2>
      {challenges.map((c, i) => (
        <div key={i} className={`challenge-item strength-${c.strength}`}>
          <p className="challenge-target">Against: {c.target}</p>
          <p className="challenge-text">{c.challenge}</p>
          <p className="challenge-meta">
            <span className={`strength-pill strength-${c.strength}`}>{c.strength}</span>
            <span className="resolution-pill">{c.resolution.replace(/_/g, ' ')}</span>
          </p>
        </div>
      ))}
    </section>
  );
}
