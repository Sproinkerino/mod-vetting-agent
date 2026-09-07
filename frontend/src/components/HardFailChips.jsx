const LABELS = {
  hate_speech: 'Hate speech',
  targeted_harassment: 'Targeted harassment',
  doxxing: 'Doxxing',
  vote_manipulation: 'Vote manipulation',
};

// §3: hard-fail chips are four, not six. undisclosed_coi and
// application_dishonesty were dropped as unservable by this pipeline --
// the UI must not render placeholder chips for them. This component only
// ever renders codes it's actually given, and only the four known ones;
// an unrecognized code is dropped rather than guessed at, since a chip
// for a check that doesn't exist is a false assurance either way.
export default function HardFailChips({ hardFails }) {
  const known = hardFails.filter((hf) => hf.code in LABELS);
  return (
    <section className="hard-fail-chips" aria-label="Hard fails">
      {known.map((hf) => (
        <span
          key={hf.code}
          className={`hard-fail-chip ${hf.triggered ? 'chip-triggered' : 'chip-clear'}`}
        >
          <span className="chip-glyph" aria-hidden="true">
            {hf.triggered ? '⚑' : '—'}
          </span>
          {LABELS[hf.code]}
          {hf.triggered && hf.finding_ids?.length > 0 && (
            <span className="chip-finding-links">
              {hf.finding_ids.map((id) => (
                <a key={id} href={`#finding-${id}`}>
                  {id}
                </a>
              ))}
            </span>
          )}
        </span>
      ))}
    </section>
  );
}
