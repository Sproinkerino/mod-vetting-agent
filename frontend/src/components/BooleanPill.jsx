// FR-C1: every boolean renders in one of three states: true, false,
// unknown. Unknown uses the `unknown` hue plus the `--` glyph -- never
// blank, never false, never a faded false.
export default function BooleanPill({ code, value }) {
  let stateClass, glyph, label;
  if (value === true) {
    stateClass = 'bool-true';
    glyph = '✓';
    label = 'true';
  } else if (value === false) {
    stateClass = 'bool-false';
    glyph = '✗';
    label = 'false';
  } else {
    stateClass = 'bool-unknown';
    glyph = '—';
    label = 'unknown';
  }
  return (
    <span className={`bool-pill ${stateClass}`} title={`${code}: ${label}`}>
      <span className="bool-code">{code}</span>
      <span className="bool-glyph" aria-hidden="true">
        {glyph}
      </span>
      <span className="visually-hidden">{label}</span>
    </span>
  );
}
