import { useMemo, useState } from 'react';
import ExpandableText from './ExpandableText';
const PAGE_SIZE = 25;
const fmtDate = (value) => new Date(value * 1000).toLocaleDateString(undefined, { year:'numeric', month:'short', day:'numeric' });

export default function ActivityExplorer({ activity = [] }) {
  const [type, setType] = useState('comment'); const [page, setPage] = useState(0); const [query, setQuery] = useState('');
  const filtered = useMemo(() => activity.filter((item) => item.type === type).filter((item) => `${item.title || ''} ${item.submission_title || ''} ${item.body} ${item.subreddit}`.toLowerCase().includes(query.toLowerCase())).sort((a,b) => b.created_utc-a.created_utc), [activity,type,query]);
  const pages = Math.max(1, Math.ceil(filtered.length/PAGE_SIZE)); const visible = filtered.slice(page*PAGE_SIZE,(page+1)*PAGE_SIZE);
  const changeType = (next) => { setType(next); setPage(0); }; const search = (next) => { setQuery(next); setPage(0); };
  return <section className='activity-section'>
    <div className='activity-heading'><div><span className='eyebrow'>Source archive</span><h2>Public comments and posts</h2><p>Raw text only · up to {PAGE_SIZE} items per page</p></div><input aria-label='Search activity' value={query} onChange={(e)=>search(e.target.value)} placeholder='Search activity' /></div>
    <div className='activity-tabs' aria-label='Activity type'>{['comment','post'].map((kind)=><button type='button' key={kind} aria-pressed={type===kind} className={type===kind?'active':''} onClick={()=>changeType(kind)}>{kind==='comment'?'Comments':'Posts'} <span>{activity.filter((item)=>item.type===kind).length}</span></button>)}</div>
    <div className='activity-list'>{visible.map((item)=><article className='activity-row' key={`${item.type}-${item.id}`}><div className='activity-meta'><span>r/{item.subreddit}</span><span>{fmtDate(item.created_utc)}</span><span>{item.score} points</span></div><h3>{item.type==='post'?(item.title||'Untitled post'):(item.submission_title||'Reddit discussion')}</h3><ExpandableText text={item.body||'No text content.'} /><a href={item.permalink} target='_blank' rel='noreferrer'>Open source ↗</a></article>)}{!visible.length&&<div className='empty-panel'>No matching {type}s.</div>}</div>
    {pages>1&&<div className='pagination'><button disabled={page===0} onClick={()=>setPage(page-1)}>Previous</button><span>Page {page+1} of {pages}</span><button disabled={page+1>=pages} onClick={()=>setPage(page+1)}>Next</button></div>}
  </section>;
}
