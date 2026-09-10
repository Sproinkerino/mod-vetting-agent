import { useMemo, useState } from 'react';
import { askArchive, startJob, waitForJob } from './lib/api';
import { groupFindingsById } from './lib/findings';
import FindingCard from './components/FindingCard';
import ActivityExplorer from './components/ActivityExplorer';
import DetectiveMascot from './components/DetectiveMascot';
import ExpandableText from './components/ExpandableText';
import { buildRedditShareText } from './lib/shareText';

const USERNAME_RE = /^[A-Za-z0-9_-]{3,20}$/;
const CATEGORIES = ['all', 'conduct', 'bias', 'judgment', 'coordination', 'doxxing', 'self_description'];
const LABELS = { conduct: 'Hostile', bias: 'Group attacks', judgment: 'Contradictions', coordination: 'Dogpiling', doxxing: 'Privacy', self_description: 'Personal details' };

export default function App() {
  const [target, setTarget] = useState('');
  const [stage, setStage] = useState('idle');
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');

  async function investigate(event) {
    event.preventDefault();
    const raw = target.trim();
    const isUrl = raw.length > 30;
    const normalized = isUrl ? raw : raw.replace(/^u\//, '');
    if ((!isUrl && !USERNAME_RE.test(normalized)) || (isUrl && !/^https?:\/\/(?:www\.)?reddit\.com\//i.test(normalized))) {
      setError('Enter a Reddit username or a full reddit.com comment URL.');
      return;
    }
    setStage('running'); setError('');
    try {
      const { job_id } = await startJob(normalized);
      const result = await waitForJob(job_id);
      if (result.status === 'error') throw new Error(result.error || 'Investigation failed.');
      setReport({ ...result.report, api_job_id: job_id });
      setStage('done');
    } catch (reason) {
      setError(reason.message.includes('fetch') ? `${reason.message} Is the local API running on port 8000?` : reason.message);
      setStage('error');
    }
  }

  if (stage === 'done') return <CaseFile report={report} onReset={() => { setStage('idle'); setReport(null); }} />;

  return <AppShell>
    <main id="main-content" className="home">
      <section className="hero">
        <div className="hero-art" aria-hidden="true"><DetectiveMascot /></div>
        <p className="kicker">REDDIT RECEIPTS, ON DEMAND</p>
        <h1>Bring the comment.<br/><em>We’ll bring the receipts.</em></h1>
        <p className="lede">Paste a Reddit comment to check it against the author’s public history—or enter a username to investigate what they’ve said before.</p>
        <form className="search-box" onSubmit={investigate}>
          <label htmlFor="reddit-target">Reddit comment URL or username</label>
          <div className="search-row">
            <span aria-hidden="true">{target.trim().length > 30 ? '↗' : 'u/'}</span>
            <input id="reddit-target" value={target} onChange={(event) => setTarget(event.target.value)} placeholder="Paste a comment or username" disabled={stage === 'running'} autoFocus aria-describedby="input-help" aria-invalid={Boolean(error)} />
            <button disabled={stage === 'running'}>{stage === 'running' ? 'Looking…' : 'Find receipts'}</button>
          </div>
          <small id="input-help">Only public Reddit activity is reviewed. Results expire from the cache after 3 days.</small>
        </form>
        {stage === 'running' && <LoadingState />}
        {error && <p className="error" role="alert">{error}</p>}
        <div className="trust-row" aria-label="Product principles"><span>✓ Exact quotes</span><span>✓ Direct source links</span><span>✓ No invented claims</span></div>
      </section>
    </main>
  </AppShell>;
}

function AppShell({ children, action }) {
  return <div className="app-shell"><a className="skip-link" href="#main-content">Skip to content</a><header className="topbar"><a className="logo" href="/" aria-label="reddit-pi home"><span>🔥</span> reddit<span>-pi</span></a><p>Receipts before replies.</p>{action}</header>{children}</div>;
}

function LoadingState() {
  return <section className="loading-card" role="status" aria-live="polite"><div className="scanner"><i /></div><div><strong>Checking public history</strong><p>Collecting activity, then verifying useful quotes against their original context. This can take a minute.</p></div></section>;
}

function CaseFile({ report, onReset }) {
  const username = report.applicant.username;
  const grouped = useMemo(() => groupFindingsById(report.findings || []), [report.findings]);
  return <AppShell action={<button className="text-button" onClick={onReset}>New search</button>}>
    <main id="main-content" className="case-page">
      <header className="case-title"><div className="case-identity"><p className="kicker">CASE FILE</p><h1>u/{username}</h1><p>{report._cache?.hit ? 'Saved scan · reused without new AI calls' : 'Fresh scan of public activity'}</p></div><div className="case-mascot"><DetectiveMascot compact /></div><div className="receipt-count"><strong>{grouped.length}</strong><span>useful receipts</span></div></header>
      {report.target_comment && <TargetComment comment={report.target_comment} />}
      <AskPanel report={report} />
      <a className="detail-cue" href="#case-details"><span>Want the full picture?</span><strong>Scroll for evidence, behavior signals and public history</strong><i aria-hidden="true">↓</i></a>
      <div id="case-details">
        <SignalStrip metrics={report.behavior_metrics || {}} findings={report.findings || []} />
      </div>
      <EvidenceShelf findings={report.findings || []} />
      <ActivityExplorer activity={report.activity || []} />
      <footer>Public posts and comments only · Quotes link to their original Reddit context · Cached for 3 days</footer>
    </main>
  </AppShell>;
}

function TargetComment({ comment }) {
  return <article className="target-card"><div className="card-label"><span>THE COMMENT</span><a href={comment.permalink} target="_blank" rel="noreferrer">Open on Reddit ↗</a></div><ExpandableText className="target-quote" text={comment.body} /><p>u/{comment.author} · r/{comment.subreddit}</p></article>;
}

function humanizeCitations(answer, sources) {
  return sources.reduce((text, source, index) => {
    const escapedId = source.id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return text.replace(new RegExp(`\\b(?:item\\s+)?${escapedId}\\b`, 'gi'), `source ${index + 1}`);
  }, answer);
}

function AskPanel({ report }) {
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');
  const suggestions = report.target_comment ? ['Does their history contradict this?', 'What have they said about this topic?', 'Find the clearest factual inconsistency'] : ['What do they say about their work?', 'Find their most hostile exchange', 'What opinions do they repeat?'];
  async function ask(event) { event.preventDefault(); if (!question.trim()) return; setBusy(true); setError(''); try { setResult(await askArchive(report.api_job_id, question.trim(), report)); } catch (reason) { setError(reason.message); } finally { setBusy(false); } }
  const sources = result ? result.sources.map((source) => ({ ...(report.activity || []).find((item) => item.id === source.id), ...source })) : [];
  const displayOpener = result ? humanizeCitations(result.opener || '', sources) : '';
  const displayAnswer = result ? humanizeCitations(result.answer, sources) : '';
  const shareText = result ? buildRedditShareText({ sources, opener: displayOpener, answer: displayAnswer, origin: window.location.origin }) : '';
  async function copy() { await navigator.clipboard.writeText(shareText); setCopied(true); window.setTimeout(() => setCopied(false), 1800); }
  return <section className="ask-card" aria-labelledby="ask-heading"><div className="ask-heading"><span className="spark">✦</span><div><p className="kicker">BUILD A CITED REPLY</p><h2 id="ask-heading">What do you want to know?</h2><p>Ask about a claim or pattern. reddit-pi answers only from the fetched archive and attaches the receipts.</p></div></div><div className="prompt-chips">{suggestions.map((suggestion) => <button type="button" key={suggestion} onClick={() => setQuestion(suggestion)}>{suggestion}</button>)}</div><form onSubmit={ask} className="ask-form"><label className="visually-hidden" htmlFor="archive-question">Question about this Redditor</label><textarea id="archive-question" rows="2" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="e.g. They say they earn $300k—does their history support that?"/><button disabled={busy || !question.trim()}>{busy ? 'Checking sources…' : 'Check the receipts →'}</button></form>{error && <p className="error" role="alert">{error}</p>}{result && <div className="reply-card" aria-live="polite"><div className="card-label"><span>COPY-READY COMEBACK</span><button type="button" onClick={copy}>{copied ? 'Copied ✓' : 'Copy'}</button></div>{displayOpener && <p className="reply-opener">{displayOpener}</p>}{sources.length > 0 && <div className="comeback-quotes">{sources.slice(0, 3).map((source, index) => <blockquote key={source.id}><span>Quote {index + 1}</span>“{(source.body || '').slice(0, 50).trim()}{(source.body || '').length > 50 ? '...' : ''}”</blockquote>)}</div>}<p className="reply-text">{displayAnswer}</p>{result.provider_fallback && <p className="provider-note">AI wording was unavailable; showing the closest retrieved evidence without inventing a conclusion.</p>}{sources.length > 0 && <div className="raw-sources"><div className="raw-sources-heading"><strong>Check the full comments</strong><span>Raw text from Reddit</span></div>{sources.map((source, index) => <article className="raw-source" key={source.id}><div><b>Source {index + 1}</b><span>{source.subreddit ? `r/${source.subreddit}` : 'Reddit'}{source.created_utc ? ` · ${new Date(source.created_utc * 1000).toLocaleDateString()}` : ''}</span></div>{source.title && <h3>{source.title}</h3>}<ExpandableText className="raw-comment" text={source.body || 'Comment text unavailable in this cached result.'} /><a href={source.permalink} target="_blank" rel="noreferrer">Open original context ↗</a></article>)}</div>}<small><a href="/">reddit-pi</a></small></div>}</section>;
}

function EvidenceShelf({ findings }) {
  const [filter, setFilter] = useState('all');
  const groups = useMemo(() => groupFindingsById(findings), [findings]);
  const visible = groups.filter((group) => filter === 'all' || group.categoryFindings.some((finding) => finding.category === filter));
  const available = CATEGORIES.filter((category) => category === 'all' || findings.some((finding) => finding.category === category));
  return <section className="evidence-section"><div className="section-heading"><div><p className="kicker">THE RECEIPTS</p><h2>Quote first. Context one tap away.</h2></div><span>{visible.length} shown</span></div><div className="filter-row" aria-label="Filter evidence">{available.map((category) => <button type="button" aria-pressed={filter === category} className={filter === category ? 'active' : ''} onClick={() => setFilter(category)} key={category}>{category === 'all' ? 'All' : LABELS[category]}</button>)}</div><div className="evidence-grid">{visible.length ? visible.map((group) => <FindingCard key={group.id} id={group.id} categoryFindings={group.categoryFindings}/>) : <p className="empty">No cited evidence in this category.</p>}</div></section>;
}

function SignalStrip({ metrics, findings }) {
  const items = [['Hostility', metrics.hostility || 0], ['Anger', metrics.anger || 0], ['Group attacks', metrics.group_hatred || 0]];
  const overall = metrics.overall || 0;
  return <section className="dashboard-overview" aria-label="Sampled behavior overview"><div className="metric-row">{items.map(([label, value], index) => <article className="metric-card" key={label}><span className={`metric-icon metric-${index}`}>{index === 0 ? '↯' : index === 1 ? '◒' : '◎'}</span><div><small>{label}</small><strong>{value}<i>/100</i></strong></div><span className="metric-change">{value > 50 ? 'Elevated' : 'Low'}</span></article>)}</div><div className="overview-row"><article className="summary-panel"><p className="kicker">SIGNAL DISTRIBUTION</p><div className="signal-bars">{items.map(([label, value]) => <div key={label}><span>{label}</span><i><b style={{ width: `${value}%` }}/></i><strong>{value}</strong></div>)}</div><small>Calculated only from cited incidents in this sample.</small></article><article className="gauge-card"><div className="gauge" style={{ '--score': `${overall * 2.7}deg` }}><div><strong>{overall}</strong><small>interaction signal</small></div></div><p>{new Set(findings.map((finding) => finding.id)).size} cited incident{new Set(findings.map((finding) => finding.id)).size === 1 ? '' : 's'}</p></article></div></section>;
}
