import { validateQuoteOffset, cardHasJudgmentFinding } from '../lib/findings';
import HighlightedBody from './HighlightedBody';

const CATEGORY_LABELS = {
  conduct: 'Conduct',
  bias: 'Bias',
  judgment: 'Judgment',
  coordination: 'Coordination',
  doxxing: 'Doxxing',
  self_description: 'Self-described',
};

function fmtDate(created_utc) {
  return new Date(created_utc * 1000).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

// Findings sharing a source comment id render as ONE card with multiple
// category tags -- categoryFindings is the group for one id.
export default function FindingCard({ id, categoryFindings }) {
  const first = categoryFindings[0];
  const anyOffsetInvalid = categoryFindings.some(
    (f) => !validateQuoteOffset(f.body, f.quote, f.quote_offset)
  );
  const showReplies = cardHasJudgmentFinding(categoryFindings);
  const isInfoOnly = categoryFindings.every((f) => f.category === 'self_description');

  return (
    <article className={`finding-card ${isInfoOnly ? 'finding-card-info' : ''}`} id={`finding-${id}`}>
      <header className="finding-card-header">
        <div className="category-tags">
          {categoryFindings.map((f) => (
            <span key={f.category} className={`category-tag tag-${f.category}`}>
              {CATEGORY_LABELS[f.category] || f.category}
              {typeof f.level === 'number' && <span className="tag-level"> · level {f.level}</span>}
            </span>
          ))}
        </div>
        <a className="permalink-link" href={first.permalink} target="_blank" rel="noreferrer">
          View on Reddit ↗
        </a>
      </header>

      <p className="finding-meta">
        r/{first.subreddit} · {fmtDate(first.created_utc)}
      </p>

      <blockquote className="parent-comment">
        {first.parent_body ? (
          <>
            <span className="parent-label">In reply to</span>
            <p className="body-text">{first.parent_body}</p>
          </>
        ) : (
          <p className="top-level-note">Top-level comment — no parent.</p>
        )}
      </blockquote>

      <HighlightedBody body={first.body} quote={first.quote} offset={first.quote_offset} />

      {anyOffsetInvalid && (
        <p className="offset-error-note" role="alert">
          One of this card's citations failed an integrity check and its level was withheld — see
          highlighted text above.
        </p>
      )}

      {showReplies && (
        <div className="replies-block">
          <span className="replies-label">What happened after</span>
          {first.replies && first.replies.length ? (
            <ul className="replies-list">
              {first.replies.map((r) => (
                <li key={r.id}>
                  <span className="reply-author">{r.author}:</span> {r.body}
                </li>
              ))}
            </ul>
          ) : (
            <p className="no-replies">No replies captured in this thread window.</p>
          )}
        </div>
      )}

      {(first.context_note || first.register_note) && (
        <div className="notes-block">
          {first.context_note && <p className="context-note">{first.context_note}</p>}
          {first.register_note && <p className="register-note">{first.register_note}</p>}
        </div>
      )}
    </article>
  );
}
