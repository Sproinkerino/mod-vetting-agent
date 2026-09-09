import { validateQuoteOffset, cardHasJudgmentFinding } from '../lib/findings';
import HighlightedBody from './HighlightedBody';

const LABELS = { conduct:'Heated exchange', bias:'Group hostility', judgment:'Disputed claim', coordination:'Mobilization', doxxing:'Privacy exposure', self_description:'Public self-disclosure' };
const fmtDate = (value) => new Date(value * 1000).toLocaleDateString(undefined, { year:'numeric', month:'short', day:'numeric' });

export default function FindingCard({ id, categoryFindings }) {
  const first = categoryFindings[0];
  const citationValid = validateQuoteOffset(first.body, first.quote, first.quote_offset);
  const anyOffsetInvalid = categoryFindings.some((f) => !validateQuoteOffset(f.body, f.quote, f.quote_offset));
  const showReplies = cardHasJudgmentFinding(categoryFindings);
  return (
    <article className='finding-card' id={`finding-${id}`}>
      <header className='finding-card-header'>
        <div className='category-tags'>{categoryFindings.map((f) => <span key={f.category} className={`category-tag tag-${f.category}`}>{LABELS[f.category] || f.category}{typeof f.level === 'number' && <span className='tag-level'> · level {f.level}</span>}</span>)}</div>
        <a className='permalink-link' href={first.permalink} target='_blank' rel='noreferrer'>View source ↗</a>
      </header>
      <p className='finding-meta'>r/{first.subreddit} · {fmtDate(first.created_utc)}</p>
      <div className='submission-heading'><span className='submission-label'>Discussion</span><h3>{first.submission_title || 'Reddit discussion'}</h3></div>
      {citationValid && <blockquote className='evidence-quote'>“{first.quote}”</blockquote>}
      <details className='context-details'><summary>View full comment{first.parent_body ? ' and context' : ''}</summary>{first.parent_body && <blockquote className='parent-comment'><span className='parent-label'>In reply to</span><p className='body-text'>{first.parent_body}</p></blockquote>}<HighlightedBody body={first.body} quote={first.quote} offset={first.quote_offset} /></details>
      {anyOffsetInvalid && <p className='offset-error-note' role='alert'>A citation failed its exact-text integrity check. Highlighting was suppressed.</p>}
      {showReplies && <div className='replies-block'><span className='replies-label'>What happened after</span>{first.replies?.length ? <ul className='replies-list'>{first.replies.map((reply) => <li key={reply.id}><strong>{reply.author}:</strong> {reply.body}</li>)}</ul> : <p className='no-replies'>No replies captured in this thread window.</p>}</div>}
    </article>
  );
}
