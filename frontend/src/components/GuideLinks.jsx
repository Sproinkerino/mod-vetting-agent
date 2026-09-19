import '../guide-links.css';

/** Compact, static discovery navigation. No loading/disabled state: links always work. */
export default function GuideLinks() {
  return <nav className="guide-links" aria-label="Reddit history guides">
    <a href="/guides/reddit-user-history/">Search Reddit history</a>
    <a href="/guides/filter-reddit-history-by-subreddit/">Filter by subreddit</a>
    <a href="/guides/verify-reddit-quotes/">Verify quotes</a>
    <a href="/guides/why-reddit-history-is-missing/">Missing history</a>
    <a href="/guides/cached-vs-fresh-reddit-search/">Cached vs fresh</a>
    <a href="/guides/methodology-and-data/">Sources and data</a>
  </nav>;
}
