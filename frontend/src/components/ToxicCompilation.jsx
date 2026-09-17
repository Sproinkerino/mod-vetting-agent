import { useState } from 'react';
import { compileToxicArchive } from '../lib/api';
import { buildToxicCompilationShareText } from '../lib/shareText';
import ExpandableText from './ExpandableText';

/** Opt-in compilation of up to ten verified comments from the selected scope. */
export default function ToxicCompilation({ report, subreddits, disabled = false }) {
  const [state, setState] = useState({ status: 'idle' });
  const scopeKey = JSON.stringify(subreddits);
  const current = state.scopeKey === scopeKey ? state : { status: 'idle' };

  async function compile() {
    setState({ status: 'loading', scopeKey });
    try {
      const result = await compileToxicArchive(report, subreddits);
      setState({ status: 'ready', scopeKey, ...result });
    } catch (error) {
      setState({ status: 'error', scopeKey, message: error.message });
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(buildToxicCompilationShareText(current));
      setState((value) => ({ ...value, copied: true, copyError: '' }));
    } catch {
      setState((value) => ({ ...value, copyError: 'Copy failed. Select the preview text and copy it manually.' }));
    }
  }

  return <section className="toxic-compilation" aria-label="Compile hostile and bigoted receipts">
    <button type="button" className="compile-toxic-button" onClick={compile}
      disabled={disabled || state.status === 'loading'} aria-busy={state.status === 'loading'}>
      <span>{state.status === 'loading' ? 'Reviewing comments…' : 'Compile Toxic Receipts'}</span>
      <small>Up to 10 strongest hostile or bigoted comments · exact quotes + sources</small>
    </button>
    <div role="status" aria-live="polite">
      {current.status === 'loading' && <p className="compilation-note">Reviewing the fetched comments in this scope. Only supported receipts will be included.</p>}
      {current.status === 'error' && <p className="error">{current.message}</p>}
      {current.status === 'ready' && <div className="reply-card">
        <div className="card-label"><span>{current.sources.length} VERIFIED RECEIPTS</span>
          {current.sources.length > 0 && <button type="button" onClick={copy}>{current.copied ? 'Copied ✓' : 'Copy compilation'}</button>}
        </div>
        <p className="reply-opener">Best comments from u/{current.username}</p>
        {!current.sources.length && <p>No clear hostile or bigoted receipt was supported in the fetched comments. Nothing was invented to fill the list.</p>}
        <div className="comeback-quotes">{current.sources.map((source) => <blockquote key={source.id}>
          <p>“{source.quote}{source.quote !== source.body ? '…' : ''}” <a href={source.permalink} target="_blank" rel="noreferrer">Source</a></p>
          <details><summary>Read full comment · r/{source.subreddit}</summary><ExpandableText text={source.body} /></details>
        </blockquote>)}</div>
        <p className="compilation-note">Selected from {current.reviewed_comment_count} fetched comments; not an exhaustive account history.{current.cached ? ' Reused without new AI calls.' : ''}</p>
        <small>Sourced by reddit-pi.</small>
        {current.copyError && <p className="error" role="alert">{current.copyError}</p>}
      </div>}
    </div>
  </section>;
}
