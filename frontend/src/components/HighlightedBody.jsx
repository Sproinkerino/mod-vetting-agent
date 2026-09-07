import { validateQuoteOffset } from '../lib/findings';

// FR-C3/C4: the quoted span renders highlighted inside the full comment
// body at quote_offset, but only after asserting body.substr(offset,
// quote.length) === quote. On mismatch: render the body unhighlighted,
// flag the error -- a misplaced highlight is a fabricated accusation
// with a different mechanism (PRD's own words, FR-C4).
export default function HighlightedBody({ body, quote, offset }) {
  const valid = validateQuoteOffset(body, quote, offset);

  if (!valid) {
    return (
      <div className="highlighted-body offset-error" role="alert">
        <p className="offset-error-banner">
          Quote offset does not match the stored comment body. Highlighting suppressed; level not
          shown for this finding. This indicates a grounding integrity failure, not a formatting
          issue.
        </p>
        <p className="body-text">{body}</p>
      </div>
    );
  }

  const before = body.slice(0, offset);
  const match = body.slice(offset, offset + quote.length);
  const after = body.slice(offset + quote.length);

  return (
    <p className="body-text highlighted-body">
      {before}
      <mark className="quote-highlight">{match}</mark>
      {after}
    </p>
  );
}
