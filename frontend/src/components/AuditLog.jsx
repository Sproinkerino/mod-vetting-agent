// FR-A1/A2: recorded with actor and timestamp; append-only, visible on
// the report. This component only renders what it's given -- it never
// mutates or reorders the log.
export default function AuditLog({ entries }) {
  return (
    <section className="audit-log">
      <h2>Audit log</h2>
      {entries.length === 0 ? (
        <p className="audit-empty">No actions recorded yet.</p>
      ) : (
        <ul>
          {entries.map((e, i) => (
            <li key={i}>
              <span className="audit-time">{new Date(e.at).toLocaleString()}</span>
              <span className="audit-actor">{e.actor}</span>
              <span className="audit-action">{e.action.replace(/_/g, ' ')}</span>
              {e.choice && <span className="audit-choice">→ {e.choice}</span>}
              {e.note && <span className="audit-note">"{e.note}"</span>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
