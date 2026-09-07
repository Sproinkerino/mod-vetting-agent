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
    <div className="integrity-strip">
      {degraded && (
        <div className="integrity-flag-banner" role="alert">
          <strong>This run has integrity issues — read the findings with that in mind.</strong>
          <ul>
            {degradedReasons(report).map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </div>
      )}
      <p className="integrity-summary">
        {p.comments_fetched} comments checked, {p.comments_flagged} flagged, {distinctComments} with
        findings ({report.findings.length} total) — window {p.window_start ? p.window_start.slice(0, 10) : '—'} to{' '}
        {p.window_end ? p.window_end.slice(0, 10) : '—'}
      </p>
    </div>
  );
}
