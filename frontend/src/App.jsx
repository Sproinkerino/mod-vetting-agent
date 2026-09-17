import { useEffect, useMemo, useRef, useState } from 'react';
import { askArchive, cancelJob, startJob, waitForJob } from './lib/api';
import { groupFindingsById } from './lib/findings';
import { communityOptions, isInSubredditScope, metricsFromFindings } from './lib/subreddits';
import FindingCard from './components/FindingCard';
import ActivityExplorer from './components/ActivityExplorer';
import DetectiveMascot from './components/DetectiveMascot';
import ExpandableText from './components/ExpandableText';
import SubredditPicker from './components/SubredditPicker';
import ToxicCompilation from './components/ToxicCompilation';
import LoadingOptions from './components/LoadingOptions';
import { buildRedditShareText, CANONICAL_SITE_URL } from './lib/shareText';
import { loadingActivity } from './lib/loadingPreview';
import { sourceExcerpt, sourceKind, sourceText } from './lib/sourceContent';

const USERNAME_RE = /^[A-Za-z0-9_-]{3,20}$/;
const CATEGORIES = ['all', 'conduct', 'bias', 'judgment', 'coordination', 'doxxing', 'self_description'];
const LABELS = { conduct: 'Hostile', bias: 'Group attacks', judgment: 'Contradictions', coordination: 'Dogpiling', doxxing: 'Privacy', self_description: 'Personal details' };
const RESUME_JOB_ID = new URLSearchParams(window.location.search).get('job');

export default function App() {
  const [target, setTarget] = useState('');
  const [analysisSubreddits, setAnalysisSubreddits] = useState([]);
  const [stage, setStage] = useState(RESUME_JOB_ID ? 'running' : 'idle');
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const [scopeRecovery, setScopeRecovery] = useState(null);
  const [progress, setProgress] = useState({ phase: RESUME_JOB_ID ? 'analyzing' : 'fetching', activity_preview: [], activity_total: 0, api_job_id: RESUME_JOB_ID });
  const activeRun = useRef(null);

  async function investigate(event, overrideSubreddits, discoverCommunities = false) {
    event?.preventDefault();
    const selectedSubreddits = overrideSubreddits ?? analysisSubreddits;
    const raw = target.trim();
    const isUrl = raw.length > 30;
    const normalized = isUrl ? raw : (raw.toLowerCase().startsWith('u/') ? raw.slice(2) : raw);
    const lowerTarget = normalized.toLowerCase();
    const isRedditUrl = lowerTarget.startsWith('https://reddit.com/') || lowerTarget.startsWith('https://www.reddit.com/') || lowerTarget.startsWith('http://reddit.com/') || lowerTarget.startsWith('http://www.reddit.com/');
    if ((!isUrl && !USERNAME_RE.test(normalized)) || (isUrl && !isRedditUrl)) {
      setError('Enter a Reddit username or a full reddit.com post or comment URL.');
      return;
    }
    const run = { controller: new AbortController(), jobId: null };
    activeRun.current = run;
    setAnalysisSubreddits(selectedSubreddits);
    setScopeRecovery(null);
    setStage('running');
    setError('');
    setProgress({ phase: 'fetching', activity_preview: [], activity_total: 0, analysis_scope: selectedSubreddits, discovery_only: discoverCommunities });
    try {
      const { job_id } = await startJob(normalized, selectedSubreddits, discoverCommunities);
      run.jobId = job_id;
      setProgress((value) => ({ ...value, api_job_id: job_id }));
      if (run.controller.signal.aborted) {
        await cancelJob(job_id).catch(() => undefined);
        return;
      }
      const result = await waitForJob(job_id, { onTick: (entry) => setProgress((value) => ({ ...value, ...entry, api_job_id: job_id })), signal: run.controller.signal });
      if (result.status === 'cancelled') return;
      if (result.status === 'scope_empty' || result.status === 'communities_ready') {
        setScopeRecovery(result);
        setStage('idle');
        return;
      }
      if (result.status === 'error') throw new Error(result.error || 'Investigation failed.');
      setReport({ ...result.report, api_job_id: job_id });
      setStage('done');
    } catch (reason) {
      if (reason.name === 'AbortError') return;
      setError(reason.message.includes('fetch') ? reason.message + ' Is the local API running on port 8000?' : reason.message);
      setStage('error');
    } finally {
      if (activeRun.current === run) activeRun.current = null;
    }
  }

  useEffect(() => {
    const jobId = RESUME_JOB_ID;
    if (!jobId) return undefined;
    const controller = new AbortController();
    const run = { controller, jobId };
    activeRun.current = run;
    waitForJob(jobId, { signal: controller.signal, onTick: (entry) => setProgress((value) => ({ ...value, ...entry, api_job_id: jobId })) })
      .then((result) => {
        if (result.status === 'done') {
          setReport({ ...result.report, api_job_id: jobId });
          setStage('done');
        } else if (result.status === 'scope_empty' || result.status === 'communities_ready') {
          setTarget(result.username || '');
          setScopeRecovery(result);
          setStage('idle');
        } else if (result.status === 'cancelled') {
          setStage('idle');
        } else if (result.status === 'error') {
          setError(result.error || 'The report could not be completed.');
          setStage('error');
        }
      })
      .catch((reason) => {
        if (reason.name !== 'AbortError') { setError(reason.message); setStage('error'); }
      })
      .finally(() => { if (activeRun.current === run) activeRun.current = null; });
    return () => { controller.abort(); if (activeRun.current === run) activeRun.current = null; };
  }, []);

  function cancelInvestigation() {
    const run = activeRun.current;
    if (!run) return;
    run.controller.abort();
    if (run.jobId) cancelJob(run.jobId).catch(() => undefined);
    activeRun.current = null;
    setStage('idle');
    setReport(null);
    setError('');
    setProgress({ phase: 'fetching', activity_preview: [], activity_total: 0 });
  }

  function reset() {
    setStage('idle');
    setReport(null);
    setError('');
  }

  if (stage === 'done') return <CaseFile report={report} onReset={reset} />;

  return <AppShell>
    <main id="main-content" className="home">
      <section className="hero">
        <div className="hero-art" aria-hidden="true"><DetectiveMascot /></div>
        <p className="kicker">REDDIT RECEIPTS, ON DEMAND</p>
        <h1>Bring the claim.<br/><em>We'll bring the receipts.</em></h1>
        <p className="lede">Paste a Reddit post or comment to check it against the author's public history, or enter a username to investigate what they have shared before.</p>
        <form className="search-box" onSubmit={investigate}>
          <label htmlFor="reddit-target">Reddit post, comment URL, or username</label>
          <div className="search-row">
            <span aria-hidden="true">{target.trim().length > 30 ? '↗' : 'u/'}</span>
            <input id="reddit-target" value={target} onChange={(event) => setTarget(event.target.value)} placeholder="Paste a post, comment, or username" disabled={stage === 'running'} autoFocus aria-describedby="input-help" aria-invalid={Boolean(error)} />
            <button disabled={stage === 'running'}>{stage === 'running' ? 'Looking...' : 'Find receipts'}</button>
          </div>
          <button type="button" className="discover-communities" disabled={stage === 'running'} onClick={(event) => investigate(event, [], true)}>
            <span aria-hidden="true">✦</span><span><strong>Find their top subreddit first</strong><small>See where they actually post before running AI analysis</small></span><b aria-hidden="true">→</b>
          </button>
          <div className="search-choice"><span>or choose communities yourself</span></div>
          <SubredditPicker value={analysisSubreddits} onChange={(next) => { setAnalysisSubreddits(next); setScopeRecovery(null); }} disabled={stage === 'running'} label="Focus the investigation" help="Optional. Only selected communities will be sent through AI analysis." showPopular />
          <small id="input-help">Only public Reddit activity is reviewed. Results are cached for 3 days.</small>
        </form>
        {stage === 'running' && <LoadingState progress={progress} scope={analysisSubreddits} onCancel={cancelInvestigation} />}
        {scopeRecovery && <ScopeRecovery recovery={scopeRecovery} onChoose={(name) => investigate(null, [name])} />}
        {error && <p className="error" role="alert">{error}</p>}
        <div className="trust-row" aria-label="Product principles"><span>✓ Exact quotes</span><span>✓ Direct source links</span><span>✓ No invented claims</span></div>
      </section>
    </main>
  </AppShell>;
}

function ScopeRecovery({ recovery, onChoose }) {
  const isDiscovery = recovery.status === 'communities_ready';
  const suggested = new Set(recovery.suggested_subreddits || []);
  const communities = (recovery.community_counts || []).filter((item) => suggested.has(item.name)).slice(0, 5);
  const requested = (recovery.requested_subreddits || []).map((name) => 'r/' + name).join(', ');
  const totalCommunities = recovery.community_total || communities.length;
  const remaining = Math.max(0, totalCommunities - communities.length);
  return <section className="scope-recovery" aria-labelledby="scope-recovery-heading">
    <p className="kicker">{isDiscovery ? 'TOP COMMUNITIES FOUND' : 'TRY A COMMUNITY THEY USE'}</p>
    <h2 id="scope-recovery-heading">{isDiscovery ? (communities.length ? 'Most active in r/' + communities[0].name : 'No public activity found') : 'Nothing in ' + (requested || 'that selection')}</h2>
    {communities.length ? <>
      <p>We found {recovery.activity_total} fetched public items across {totalCommunities} communit{totalCommunities === 1 ? 'y' : 'ies'}. Their most-used communities are:</p>
      <div className="scope-recovery-list">{communities.map((item, index) => <button type="button" key={item.name} onClick={() => onChoose(item.name)}><span><strong>r/{item.name}</strong>{index === 0 && <em>Recommended</em>}</span><b>{item.count} item{item.count === 1 ? '' : 's'} →</b></button>)}</div>
      {remaining > 0 && <small>Plus {remaining} other communit{remaining === 1 ? 'y' : 'ies'} in the fetched history.</small>}
    </> : <p>No public posts or comments were found for this account in the fetched history.</p>}
  </section>;
}

function AppShell({ children, action }) {
  return <div className="app-shell"><a className="skip-link" href="#main-content">Skip to content</a><header className="topbar"><a className="logo" href="/" aria-label="reddit-pi home"><span>◆</span> reddit<span>-pi</span></a><p>Receipts before replies.</p>{action}</header>{children}</div>;
}

function LoadingState({ progress, scope = [], onCancel }) {
  const activity = loadingActivity(progress);
  const analyzing = progress.phase === 'analyzing';
  const discovering = Boolean(progress.discovery_only);
  const scopeText = scope.length ? scope.map((name) => 'r/' + name).join(', ') : 'all communities';
  return <section className="loading-card" aria-label="Investigation progress">
    <div className="loading-status">
      <div className="loading-status-copy" role="status" aria-live="polite"><div className="scanner"><i /></div><div><strong>{discovering ? 'Finding their top communities...' : analyzing ? 'History loaded. Analyzing now...' : 'Fetching public history...'}</strong><p>{discovering ? 'Counting public posts and comments. No AI analysis is running yet.' : analyzing ? progress.activity_total + ' scoped public items found. You can start reading while deeper analysis continues.' : 'Loading activity from ' + scopeText + '.'}</p></div></div>
      <button type="button" className="cancel-search" onClick={onCancel}>Cancel & edit search</button>
    </div>
    <LoadingOptions jobId={progress.api_job_id} />
    {activity.length > 0 && <div className="loading-preview"><div className="loading-preview-head"><strong>Recent posts and comments</strong><span>Analysis is still running</span></div><div className="loading-preview-list">{activity.map((item) => <article key={item.type + '-' + item.id}><div className="loading-preview-type"><b>{sourceKind(item)}</b><span>r/{item.subreddit}</span></div><p>{sourceExcerpt(item, 160)}</p><div>{item.permalink && <a href={item.permalink} target="_blank" rel="noreferrer">View source ↗</a>}</div></article>)}</div></div>}
  </section>;
}

function CaseFile({ report, onReset }) {
  const username = report.applicant.username;
  const availableCommunities = useMemo(() => communityOptions(report.activity || []), [report.activity]);
  const [viewSubreddits, setViewSubreddits] = useState(report.analysis_scope || []);
  const scopedActivity = useMemo(() => (report.activity || []).filter((item) => isInSubredditScope(item, viewSubreddits)), [report.activity, viewSubreddits]);
  const scopedFindings = useMemo(() => (report.findings || []).filter((finding) => isInSubredditScope(finding, viewSubreddits)), [report.findings, viewSubreddits]);
  const metrics = useMemo(() => viewSubreddits.length ? metricsFromFindings(scopedFindings) : (report.behavior_metrics || {}), [report.behavior_metrics, scopedFindings, viewSubreddits]);
  const grouped = useMemo(() => groupFindingsById(scopedFindings), [scopedFindings]);

  return <AppShell action={<button className="text-button" onClick={onReset}>New search</button>}>
    <main id="main-content" className="case-page">
      <header className="case-title"><div className="case-identity"><p className="kicker">CASE FILE</p><h1>u/{username}</h1><p>{report._cache?.hit ? 'Saved scan · reused without new AI calls' : 'Fresh scan of public activity'}</p></div><div className="case-mascot"><DetectiveMascot compact /></div><div className="receipt-count"><strong>{grouped.length}</strong><span>visible receipts</span></div></header>
      {(report.target_content || report.target_comment) && <TargetContent content={report.target_content || report.target_comment} />}
      <AskPanel report={report} subreddits={viewSubreddits} onScopeChange={setViewSubreddits} options={availableCommunities} />
      <a className="detail-cue" href="#case-details"><span>Want the full picture?</span><strong>Scroll for evidence, behavior signals and public history</strong><i aria-hidden="true">↓</i></a>
      <div id="case-details">
        <ResultsScopeBar value={viewSubreddits} onChange={setViewSubreddits} options={availableCommunities} visibleCount={scopedActivity.length} />
        <SignalStrip metrics={metrics} findings={scopedFindings} />
      </div>
      <EvidenceShelf findings={scopedFindings} />
      <ActivityExplorer activity={scopedActivity} />
      <footer>Public posts and comments only · Quotes link to their original Reddit context · Cached for 3 days</footer>
    </main>
  </AppShell>;
}

function ResultsScopeBar({ value, onChange, options, visibleCount }) {
  return <section className="results-scope" aria-label="Filter completed analysis">
    <div><p className="kicker">CASE SCOPE</p><strong>{value.length ? value.map((name) => 'r/' + name).join(', ') : 'All analyzed communities'}</strong><span>{visibleCount} public items visible</span></div>
    <SubredditPicker value={value} onChange={onChange} options={options} label="Filter this case file" help="Updates metrics, evidence and the source archive without another AI call." variant="compact" />
  </section>;
}

function TargetContent({ content }) {
  const kind = sourceKind(content);
  const body = content.type === 'post' && content.title === content.body ? '' : content.body;
  return <article className="target-card"><div className="card-label"><span>THE {kind.toUpperCase()}</span><a href={content.permalink} target="_blank" rel="noreferrer">Open on Reddit ↗</a></div>{content.type === 'post' && content.title && <h2>{content.title}</h2>}{body && <ExpandableText className="target-quote" text={body} />}<p>u/{content.author} · r/{content.subreddit}</p></article>;
}

function humanizeCitations(answer, sources) {
  return sources.reduce((text, source, index) => text.split(source.id).join('source ' + (index + 1)), answer);
}
function AskPanel({ report, subreddits, onScopeChange, options }) {
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');
  const [sourceCount, setSourceCount] = useState(1);
  const suggestions = (report.target_content || report.target_comment) ? ['Does their history contradict this?', 'What have they said about this topic?', 'Find the clearest factual inconsistency'] : ['What do they say about their work?', 'Find their most hostile exchange', 'What opinions do they repeat?'];

  function changeScope(next) {
    onScopeChange(next);
    setResult(null);
    setError('');
  }

  async function ask(event) {
    event.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError('');
    try {
      setResult(await askArchive(report.api_job_id, question.trim(), report, sourceCount, subreddits));
    } catch (reason) {
      setError(reason.message);
    } finally {
      setBusy(false);
    }
  }

  const sources = result ? result.sources.map((source) => ({ ...(report.activity || []).find((item) => item.id === source.id), ...source })) : [];
  const displayOpener = result ? humanizeCitations(result.opener || '', sources) : '';
  const displayAnswer = result ? humanizeCitations(result.answer, sources) : '';
  const shareText = result ? buildRedditShareText({ sources, opener: displayOpener, answer: displayAnswer }) : '';

  async function copy() {
    await navigator.clipboard.writeText(shareText);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  return <section className="ask-card" aria-labelledby="ask-heading">
    <div className="ask-heading"><span className="spark">✦</span><div><p className="kicker">BUILD A CITED REPLY</p><h2 id="ask-heading">What do you want to know?</h2><p>Ask about a claim or pattern. The agent reviews only the communities selected below, then attaches exact receipts.</p></div></div>
    <ToxicCompilation report={report} subreddits={subreddits} disabled={busy} />
    <div className="ask-controls">
      <SubredditPicker value={subreddits} onChange={changeScope} options={options} disabled={busy} label="Search within" help="All analyzed communities when empty." variant="compact" />
      <div className="source-count-control"><span id="source-count-label">Sources in reply</span><div className="source-count-tabs" role="group" aria-labelledby="source-count-label">{[1, 2, 3].map((count) => <button type="button" key={count} aria-pressed={sourceCount === count} disabled={busy} onClick={() => { setSourceCount(count); setResult(null); }}>{count}</button>)}</div></div>
    </div>
    <div className="prompt-chips">{suggestions.map((suggestion) => <button type="button" key={suggestion} onClick={() => setQuestion(suggestion)}>{suggestion}</button>)}</div>
    <form onSubmit={ask} className="ask-form"><label className="visually-hidden" htmlFor="archive-question">Question about this Redditor</label><textarea id="archive-question" rows="2" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="e.g. Find racist remarks or anything about colour"/><button disabled={busy || !question.trim()}>{busy ? 'Checking sources...' : 'Check the receipts →'}</button></form>
    {error && <p className="error" role="alert">{error}</p>}
    {result && <div className="reply-card" aria-live="polite"><div className="card-label"><span>COPY-READY COMEBACK</span><button type="button" onClick={copy}>{copied ? 'Copied ✓' : 'Copy'}</button></div>{displayOpener && <p className="reply-opener">{displayOpener}</p>}{sources.length > 0 && <div className="comeback-quotes">{sources.slice(0, 3).map((source, index) => <blockquote key={source.id}><span>{sourceKind(source)} {index + 1}</span>“{sourceExcerpt(source)}”</blockquote>)}</div>}<p className="reply-text">{displayAnswer}</p>{result.provider_fallback && <p className="provider-note">AI wording was unavailable, so no unsupported conclusion was generated.</p>}{sources.length > 0 && <div className="raw-sources"><div className="raw-sources-heading"><strong>Check the full posts and comments</strong><span>Raw text from Reddit</span></div>{sources.map((source, index) => <article className="raw-source" key={source.id}><div><b>Source {index + 1}</b><span>{source.subreddit ? 'r/' + source.subreddit : 'Reddit'}{source.created_utc ? ' · ' + new Date(source.created_utc * 1000).toLocaleDateString() : ''}</span></div>{source.type === 'post' && source.title && <h3>{source.title}</h3>}{(source.type !== 'post' || source.body !== source.title) && <ExpandableText className="raw-comment" text={source.type === 'post' ? (source.body || 'Post text unavailable.') : sourceText(source)} />}<a href={source.permalink} target="_blank" rel="noreferrer">Open original context ↗</a></article>)}</div>}<small>This reply was generated by reddit-pi. <a href={CANONICAL_SITE_URL}>Website</a></small></div>}
  </section>;
}

function EvidenceShelf({ findings }) {
  const [filter, setFilter] = useState('all');
  const groups = useMemo(() => groupFindingsById(findings), [findings]);
  const visible = groups.filter((group) => filter === 'all' || group.categoryFindings.some((finding) => finding.category === filter));
  const available = CATEGORIES.filter((category) => category === 'all' || findings.some((finding) => finding.category === category));
  return <section className="evidence-section"><div className="section-heading"><div><p className="kicker">THE RECEIPTS</p><h2>Quote first. Context one tap away.</h2></div><span>{visible.length} shown</span></div><div className="filter-row" aria-label="Filter evidence">{available.map((category) => <button type="button" aria-pressed={filter === category} className={filter === category ? 'active' : ''} onClick={() => setFilter(category)} key={category}>{category === 'all' ? 'All' : LABELS[category]}</button>)}</div><div className="evidence-grid">{visible.length ? visible.map((group) => <FindingCard key={group.id} id={group.id} categoryFindings={group.categoryFindings}/>) : <p className="empty">No cited evidence in this scope and category.</p>}</div></section>;
}

function SignalStrip({ metrics, findings }) {
  const items = [['Hostility', metrics.hostility || 0], ['Anger', metrics.anger || 0], ['Group attacks', metrics.group_hatred || 0]];
  const overall = metrics.overall || 0;
  const incidentCount = new Set(findings.map((finding) => finding.id)).size;
  return <section className="dashboard-overview" aria-label="Scoped behavior overview"><div className="metric-row">{items.map(([label, value], index) => <article className="metric-card" key={label}><span className={'metric-icon metric-' + index}>{index === 0 ? '↯' : index === 1 ? '◒' : '◎'}</span><div><small>{label}</small><strong>{value}<i>/100</i></strong></div><span className="metric-change">{value > 50 ? 'Elevated' : 'Low'}</span></article>)}</div><div className="overview-row"><article className="summary-panel"><p className="kicker">SCOPED SIGNALS</p><div className="signal-bars">{items.map(([label, value]) => <div key={label}><span>{label}</span><i><b style={{ width: value + '%' }}/></i><strong>{value}</strong></div>)}</div><small>Recalculated only from cited incidents visible in this community scope.</small></article><article className="gauge-card"><div className="gauge" style={{ '--score': overall * 2.7 + 'deg' }}><div><strong>{overall}</strong><small>interaction signal</small></div></div><p>{incidentCount} cited incident{incidentCount === 1 ? '' : 's'}</p></article></div></section>;
}