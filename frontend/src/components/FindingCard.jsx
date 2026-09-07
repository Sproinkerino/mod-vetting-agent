import { validateQuoteOffset, cardHasJudgmentFinding } from '../lib/findings';
import HighlightedBody from './HighlightedBody';
import CategoryBlock from './CategoryBlock';

function fmtDate(created_utc) {
  return new Date(created_utc * 1000).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

// FR-C5: findings sharing a source comment id render as ONE card with
// multiple category tags -- categoryFindings is the group for one id.
export default function FindingCard({ id, categoryFindings }) {
  const first = categoryFindings[0];
  const anyOffsetInvalid = categoryFindings.some(
    (f) => !validateQuoteOffset(f.body, f.quote, f.quote_offset)
  );
  const showReplies = cardHasJudgmentFinding(categoryFindings); // FR-C7

  return (
    <article className="finding-card" id={`finding-${id}`} data-integrity={anyOffsetInvalid ? 'error' : 'ok'}>
      <header className="finding-card-header">
        <div className="category-tags">
          {categoryFindings.map((f) => (
            <span key={f.category} className={`category-tag tag-${f.category}`}>
              {f.category}
            </span>
          ))}
        </div>
        <a className="permalink-link" href={first.permalink} target="_blank" rel="noreferrer">
          {/* FR-C9: permalink opens in a new tab, present on every card without exception */}
          View on Reddit ↗
        </a>
      </header>

      <p className="finding-meta">
        r/{first.subreddit} · {fmtDate(first.created_utc)}
      </p>

      {/* FR-C2: parent renders expanded on first paint, no toggle. If
          parent_body is null, the card states the comment is top-level. */}
      <blockquote className="parent-comment">
        {first.parent_body ? (
          <>
            <span className="parent-label">Parent comment</span>
            <p className="body-text">{first.parent_body}</p>
          </>
        ) : (
          <p className="top-level-note">This is a top-level comment — no parent.</p>
        )}
      </blockquote>

      {/* FR-C3/C4: highlighted quote inside the full body. If categories on
          this card disagree on offset validity (shouldn't happen since
          they share one body/quote per comment in practice, but handled
          defensively), each category's own quote is checked independently
          below via its own HighlightedBody render is redundant since body
          is shared -- render once using the first entry. */}
      <HighlightedBody body={first.body} quote={first.quote} offset={first.quote_offset} />

      <div className="category-blocks">
        {categoryFindings.map((f) => (
          <CategoryBlock
            key={f.category}
            category={f.category}
            level={anyOffsetInvalid ? null : f.level}
            answers={f.answers}
          />
        ))}
      </div>

      {/* FR-C7: subsequent-replies block only when the card carries a
          judgment finding */}
      {showReplies && (
        <div className="replies-block">
          <span className="replies-label">Subsequent replies (thread continuation window)</span>
          {first.replies && first.replies.length ? (
            <ul className="replies-list">
              {first.replies.map((r) => (
                <li key={r.id}>
                  <span className="reply-author">{r.author}:</span> {r.body}
                </li>
              ))}
            </ul>
          ) : (
            <p className="no-replies">No replies captured in this thread continuation.</p>
          )}
        </div>
      )}

      {/* FR-C8: register_note/context_note render when present, visually
          distinct from the booleans */}
      {(first.context_note || first.register_note) && (
        <div className="notes-block">
          {first.context_note && (
            <p className="context-note">
              <span className="note-label">Context:</span> {first.context_note}
            </p>
          )}
          {first.register_note && (
            <p className="register-note">
              <span className="note-label">Register:</span> {first.register_note}
            </p>
          )}
        </div>
      )}
    </article>
  );
}
