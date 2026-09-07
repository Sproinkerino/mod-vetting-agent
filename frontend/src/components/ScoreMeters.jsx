const CATEGORY_LABELS = {
  conduct: 'Conduct',
  bias: 'Bias',
  judgment: 'Judgment',
  coordination: 'Coordination',
};

// FR-R2: level and anchor render verbatim from JSON -- no colour scale,
// no red/amber/green, no composite/overall score anywhere.
// FR-R3: level > 0 with empty finding_ids renders as an error, not a score.
export default function ScoreMeters({ scores, snippets }) {
  return (
    <section className="score-meters" aria-label="Scores">
      {Object.entries(scores).map(([category, score]) => {
        const isInvalid = score.level > 0 && (!score.finding_ids || score.finding_ids.length === 0);
        return (
          <div key={category} className={`score-meter ${isInvalid ? 'score-meter-error' : ''}`}>
            <span className="score-category">{CATEGORY_LABELS[category] || category}</span>
            {isInvalid ? (
              <p className="score-error" role="alert">
                Level {score.level} reported with no supporting findings — not a valid score, dropped
                per the level&gt;0-requires-finding_ids rule.
              </p>
            ) : (
              <>
                <span className="score-level">{score.level}</span>
                <span className="score-anchor">{score.anchor}</span>
                {score.finding_ids && score.finding_ids.length > 0 && (
                  <div className="score-finding-links">
                    {score.finding_ids.map((id) => (
                      <a key={id} href={`#finding-${id}`} className="finding-link">
                        {snippets?.get(id) || id}
                      </a>
                    ))}
                  </div>
                )}
                {/* FR-R4: contradicting_finding_ids render alongside the
                    score they cut against, at equal visual weight -- not
                    implemented by the backend yet (needs stages 3/4), so
                    this only renders when actually present. */}
                {score.contradicting_finding_ids && score.contradicting_finding_ids.length > 0 && (
                  <div className="score-contradicting">
                    <span className="contradicting-label">Contradicting evidence:</span>
                    {score.contradicting_finding_ids.map((id) => (
                      <a key={id} href={`#finding-${id}`} className="finding-link">
                        {snippets?.get(id) || id}
                      </a>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        );
      })}
    </section>
  );
}
