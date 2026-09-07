// FR-I1-I4. Renders above all report content.
export function isDegraded(report) {
  const p = report.provenance;
  return (
    p.findings_dropped_ungrounded > 3 ||
    (p.unparseable_count ?? 0) > 0 ||
    (typeof p.triage_flag_rate === 'number' && p.triage_flag_rate < 0.02) ||
    !!p.any_stage_excluded
  );
}

function degradedReasons(report) {
  const reasons = [];
  const p = report.provenance;
  if (p.findings_dropped_ungrounded > 3) reasons.push(`${p.findings_dropped_ungrounded} findings dropped (ungrounded)`);
  if ((p.unparseable_count ?? 0) > 0) reasons.push(`${p.unparseable_count} unparseable item(s)`);
  if (typeof p.triage_flag_rate === 'number' && p.triage_flag_rate < 0.02) {
    reasons.push(`triage flag rate ${(p.triage_flag_rate * 100).toFixed(1)}% below the 2% floor`);
  }
  if (p.any_stage_excluded) reasons.push('one or more stages have excluded items');
  return reasons;
}

export default function RunIntegrityStrip({ report }) {
  const degraded = isDegraded(report);
  const p = report.provenance;
  const distinctComments = new Set(report.findings.map((f) => f.id)).size;

  return (
    <div className={`integrity-strip ${degraded ? 'integrity-degraded' : ''}`}>
      {degraded && (
        <div className="integrity-flag-banner" role="alert">
          <strong>Degraded run</strong> — score meters suppressed, vote blocked until cleared at the gate.
          <ul>
            {degradedReasons(report).map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}
      <dl className="integrity-facts">
        <div>
          <dt>Window</dt>
          <dd>
            {p.window_start ? p.window_start.slice(0, 10) : '—'} – {p.window_end ? p.window_end.slice(0, 10) : '—'}
          </dd>
        </div>
        <div>
          <dt>Fetched</dt>
          <dd>{p.comments_fetched}</dd>
        </div>
        <div>
          <dt>Flagged</dt>
          <dd>{p.comments_flagged}</dd>
        </div>
        <div>
          {/* FR-I2: headline count is distinct source comments, total findings secondary */}
          <dt>Findings</dt>
          <dd>
            {distinctComments} comments <span className="secondary-count">({report.findings.length} findings)</span>
          </dd>
        </div>
        <div>
          <dt>Dropped (ungrounded)</dt>
          <dd>{p.findings_dropped_ungrounded}</dd>
        </div>
        <div>
          <dt>Unparseable</dt>
          <dd>{p.unparseable_count ?? 0}</dd>
        </div>
        <div>
          <dt>Rubric</dt>
          <dd>{report.contract.rubric_version}</dd>
        </div>
        <div>
          <dt>Contract</dt>
          <dd className="mono">{report.contract.prompt_template_hash}</dd>
        </div>
      </dl>
    </div>
  );
}
