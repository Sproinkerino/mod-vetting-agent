import { useMemo, useState } from 'react';
import { askArchive, startJob, waitForJob } from './lib/api';
import { groupFindingsById, buildSnippetMap } from './lib/findings';
import FindingCard from './components/FindingCard';
import RunIntegrityStrip from './components/RunIntegrityStrip';
import HardFailChips from './components/HardFailChips';
import ScoreMeters from './components/ScoreMeters';
import ActivityExplorer from './components/ActivityExplorer';
import DetectiveMascot from './components/DetectiveMascot';

const USERNAME_RE = /^[A-Za-z0-9_-]{3,20}$/;
const CATEGORIES = ['all', 'conduct', 'bias', 'judgment', 'coordination', 'doxxing', 'self_description'];
const CATEGORY_LABELS = { conduct:'Heated exchanges', bias:'Group hostility', judgment:'Disputed claims', coordination:'Mobilization', doxxing:'Privacy exposure', self_description:'Self-disclosures' };

export default function App() {
  const [username, setUsername] = useState('');
  const [stage, setStage] = useState('idle');
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [elapsedMs, setElapsedMs] = useState(0);

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = username.trim().replace(/^u\//, '');
    if (!USERNAME_RE.test(trimmed)) {
      setError('Enter a valid Reddit username (3–20 letters, numbers, underscores, or hyphens).');
      return;
    }
    setStage('running');
    setError(null);
    setElapsedMs(0);
    try {
      const { job_id } = await startJob(trimmed);
      const result = await waitForJob(job_id, { onTick: (_entry, ms) => setElapsedMs(ms) });
      if (result.status === 'error') throw new Error(result.error || 'Analysis failed.');
      setReport({ ...result.report, api_job_id: job_id });
      setStage('done');
    } catch (err) {
      setError(err.message.includes('fetch') ? `${err.message} Is the local API running on port 8000?` : err.message);
      setStage('error');
    }
  }

  if (stage === 'done') {
    return <Dashboard report={report} onNewSearch={() => { setStage('idle'); setReport(null); }} />;
  }

  return (
    <main className='landing-shell'>
      <nav className='brand-bar'>
        <div className='brand-mark'>RD</div>
        <span>Reddit Detective</span>
        <span className='local-badge'>Local analysis</span>
      </nav>
      <section className='hero-panel'>
        <DetectiveMascot />
        <div className='eyebrow'>Behavioral evidence · public comments</div>
        <h1>Find the pattern behind personal attacks.</h1>
        <p className='hero-copy'>Review a Reddit account for cited, contextual evidence of targeted hostility and ad hominem behavior. Every signal links back to the source.</p>
        <form onSubmit={handleSubmit} className='detective-search'>
          <span className='input-prefix'>u/</span>
          <input aria-label='Reddit username' value={username} onChange={(e) => setUsername(e.target.value)} placeholder='username' disabled={stage === 'running'} autoFocus />
          <button type='submit' disabled={stage === 'running'}>{stage === 'running' ? 'Investigating…' : 'Investigate account'}</button>
        </form>
        {stage === 'running' && <Progress elapsedMs={elapsedMs} />}
        {error && <p className='search-error' role='alert'>{error}</p>}
        <div className='scope-note'>
          <strong>What this does</strong>
          <span>Samples up to 300 recent public comments, identifies potential incidents, then checks each against conversation context. Findings are evidence—not a diagnosis or a verdict about a person.</span>
        </div>
      </section>
    </main>
  );
}

function Progress({ elapsedMs }) {
  const seconds = Math.round(elapsedMs / 1000);
  const step = seconds < 15 ? 0 : seconds < 35 ? 1 : 2;
  const labels = ['Collecting public comments', 'Screening for behavioral signals', 'Verifying context and citations'];
  return (
    <div className='progress-card' role='status'>
      <div className='progress-head'><strong>{labels[step]}</strong><span>{seconds}s</span></div>
      <div className='progress-track'><span style={{ width: `${Math.min(92, 15 + seconds)}%` }} /></div>
      <p>You can leave this tab open. Context verification is the longest step.</p>
    </div>
  );
}

function Dashboard({ report, onNewSearch }) {
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');
  const allGroups = useMemo(() => groupFindingsById(report.findings).sort((a, b) => b.categoryFindings[0].created_utc - a.categoryFindings[0].created_utc), [report.findings]);
  const snippets = useMemo(() => buildSnippetMap(report.findings), [report.findings]);
  const groups = allGroups.filter((group) => {
    const categoryMatch = filter === 'all' || group.categoryFindings.some((f) => f.category === filter);
    const text = `${group.categoryFindings[0].body} ${group.categoryFindings[0].subreddit}`.toLowerCase();
    return categoryMatch && text.includes(query.toLowerCase());
  });
  const p = report.provenance;

  return (
    <main className='dashboard-shell'>
      <header className='dashboard-nav'>
        <div className='brand-lockup'><div className='brand-mark'>RD</div><span>Reddit Detective</span></div>
        <button className='ghost-button' onClick={onNewSearch}>New investigation</button>
      </header>
      <section className='case-header'>
        <div><div className='eyebrow'>Investigation report</div><h1>u/{report.applicant.username}</h1><p>Public behavioral signals with source-level context</p></div>
        <div className='case-status'><span className='status-dot' /> {report._cache?.hit ? `Cached result · ${Math.max(1, Math.round(report._cache.age_seconds / 3600))}h old` : 'Fresh analysis'}</div>
      </section>
      <RunIntegrityStrip report={report} />
      <HardFailChips hardFails={report.hard_fails} snippets={snippets} />
      <ScoreMeters scores={report.scores} snippets={snippets} />
      <AskTheArchive report={report} />
      <BehaviorSummary metrics={report.behavior_metrics} />
      <section className='insight-grid'>
        <div className='panel category-panel'>
          <div className='panel-heading'><div><span className='eyebrow'>Signal mix</span><h2>What the evidence contains</h2></div></div>
          <CategoryBars findings={report.findings} />
        </div>
        <div className='panel context-panel'>
          <span className='eyebrow'>Sample coverage</span><h2>What was reviewed</h2>
          <p>{p.comments_fetched} public comments in the displayed date window. Scores describe cited behavior, not personality or probability.</p>
          <dl><div><dt>Coverage</dt><dd>{p.window_start?.slice(0, 10) || '—'} → {p.window_end?.slice(0, 10) || '—'}</dd></div><div><dt>Grounding</dt><dd>{p.findings_dropped_ungrounded} unsupported signal(s) removed</dd></div><div><dt>Review state</dt><dd>Human interpretation required</dd></div></dl>
        </div>
      </section>
      <section className='evidence-section'>
        <div className='evidence-heading'><div><span className='eyebrow'>Evidence log</span><h2>{groups.length} cited conversation{groups.length === 1 ? '' : 's'}</h2></div><input aria-label='Search evidence' value={query} onChange={(e) => setQuery(e.target.value)} placeholder='Search quote or subreddit' /></div>
        <div className='filter-tabs' role='group' aria-label='Filter findings by category'>
          {CATEGORIES.map((category) => <button key={category} className={filter === category ? 'active' : ''} onClick={() => setFilter(category)}>{category === 'all' ? 'All evidence' : CATEGORY_LABELS[category]}</button>)}
        </div>
        {groups.length ? groups.map((g) => <FindingCard key={g.id} id={g.id} categoryFindings={g.categoryFindings} />) : <div className='empty-panel'>No evidence matches this filter.</div>}
      </section>
      <ActivityExplorer activity={report.activity || []} />
      <footer className='report-footer'>Method: {report.contract.rubric_version} · {report.contract.prompt_template_hash} · Sampled public data · Purge after {p.purge_after}</footer>
    </main>
  );
}

function CategoryBars({ findings }) {
  const counts = CATEGORIES.slice(1).map((category) => ({ category, count: new Set(findings.filter((f) => f.category === category).map((f) => f.id)).size }));
  const max = Math.max(1, ...counts.map((item) => item.count));
  return <div className='bar-list'>{counts.map(({ category, count }) => <div className='bar-row' key={category}><span>{CATEGORY_LABELS[category]}</span><div className='bar-track'><i style={{ width: `${(count / max) * 100}%` }} /></div><strong>{count}</strong></div>)}</div>;
}

function BehaviorSummary({ metrics = {} }) {
  const rows = [['Hostility', metrics.hostility || 0], ['Anger / escalation', metrics.anger || 0], ['Group hatred', metrics.group_hatred || 0]];
  return <section className='behavior-summary'><div className='overall-score'><span className='eyebrow'>Toxic interaction signal</span><strong>{metrics.overall || 0}</strong><small>/ 100</small><div className='overall-track'><i style={{ width: `${metrics.overall || 0}%` }} /></div></div><div className='summary-copy'><h2>What is this user’s public interaction style like?</h2><p>{metrics.summary || 'Run a fresh analysis to generate a behavior summary.'}</p><div className='behavior-rows'>{rows.map(([label, value]) => <div key={label}><span>{label}</span><div><i style={{ width: `${value}%` }} /></div><strong>{value}</strong></div>)}</div><small>{metrics.basis || 'Based only on cited incidents in the sampled history.'}</small></div></section>;
}

function AskTheArchive({ report }) {
  const [question, setQuestion] = useState(''); const [result, setResult] = useState(null); const [busy, setBusy] = useState(false); const [copied, setCopied] = useState(false); const [error, setError] = useState('');
  async function submit(event) { event.preventDefault(); if (!question.trim()) return; setBusy(true); setError(''); try { setResult(await askArchive(report.api_job_id, question.trim())); } catch (err) { setError(err.message); } finally { setBusy(false); } }
  const copyText = result ? `Claim check for u/${report.applicant.username}\n\n${result.answer}\n\n${result.sources.map((source)=>`Source: ${source.permalink}`).join('\n')}\n\nCheck a Redditor's public history: ${window.location.origin}` : '';
  async function copy() { await navigator.clipboard.writeText(copyText); setCopied(true); setTimeout(()=>setCopied(false),1800); }
  return <section className='ask-panel'><div className='ask-intro'><span className='eyebrow'>Ask the archive</span><h2>What do you want to verify about u/{report.applicant.username}?</h2><p>Ask about a public claim, opinion, job, or apparent contradiction. Answers use only fetched statements and include source links.</p></div><form className='ask-form' onSubmit={submit}><input value={question} onChange={(e)=>setQuestion(e.target.value)} placeholder='e.g. Have they said anything inconsistent about their job?' aria-label='Question about this public archive'/><button disabled={busy}>{busy?'Checking…':'Find evidence'}</button></form>{error&&<p className='ask-error' role='alert'>{error}</p>}{result&&<div className='share-result'><div className='share-copy'><strong>Claim check for u/{report.applicant.username}</strong><p>{result.answer}</p>{result.sources.map((source)=><a key={source.id} href={source.permalink} target='_blank' rel='noreferrer'>Source: {source.title||source.id} ↗</a>)}<small>Check a Redditor’s public history: {window.location.origin}</small></div><button onClick={copy}>{copied?'Copied':'Copy result'}</button></div>}</section>;
}
