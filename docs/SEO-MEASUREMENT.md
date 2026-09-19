# Search and performance measurement

## Baseline and what it means

The initial production page was an empty React root without canonical/social metadata or a sitemap. Local build before optimization: JS 243.65 kB (78.96 kB gzip), CSS 26.02 kB (5.87 kB gzip). Guides are static, script-free HTML and use system fonts. API serving now applies gzip for responses over 1 kB, immutable one-year caching to hashed assets, revalidation to HTML, and no-store to job data/resume pages. Verify these policies on production after release; local tests alone do not establish CDN behavior.

These build measurements are not field Core Web Vitals. No field LCP, INP, CLS, search impressions, or ranking improvement has been verified. Do not interpret network transfer size as user-perceived loading time.

## Mobile Lighthouse lab baseline: 19 September 2026

Chrome Lighthouse 12.8.2 ran locally against the deployed `https://reddit-pi.live/` homepage with its mobile profile. Before the font change, repeated runs measured LCP between 2.8 and 3.08 seconds and reported about 312 milliseconds of render-blocking savings. Removing the external Google Fonts stylesheet and using the native UI font stack eliminated that opportunity. The final deployed commit `55f9044` measured: Performance 99, Accessibility 100, Best Practices 100, SEO 100, FCP 1.438 seconds, LCP 1.485 seconds, CLS 0, and TBT 30 milliseconds. The color-contrast audit and render-blocking audit both pass.

This is reproducible lab evidence from one machine and network, not real-user CrUX data. PageSpeed Insights continued to return HTTP 429, so its report and field-data sections remain unavailable. Recheck multiple runs and use Search Console Core Web Vitals when enough real-user traffic exists.

## Account access needed

Use an authorized Google Search Console account to add the Domain property reddit-pi.live. Follow its exact DNS verification instructions in Namecheap; do not delete unrelated TXT records. Submit https://reddit-pi.live/sitemap.xml after the release is verified. Inspect the homepage and every guide using URL Inspection and record selected canonical, indexing status, and any render errors. Submit only intended public landing pages, never job URLs.

Search Console access is not implied by access to Render or Namecheap. Do not reuse unrelated Google tokens found on disk or claim ownership verification without evidence.

The public DNS check on 19 September 2026 found no Google site-verification TXT record. IndexNow is implemented separately for participating search engines: the public key file proves host control, and `python scripts/submit_indexnow.py` submits only HTTPS URLs from the canonical sitemap after validating their host and excluding query strings. IndexNow notification does not guarantee crawling, indexing, or ranking and does not replace Search Console.

## Weekly checks

- Search Console: indexed intended pages, excluded result URLs, crawl errors, queries, impressions, clicks, click-through rate, average position. Compare equal date windows and annotate release dates.
- PageSpeed Insights: mobile homepage and each template; distinguish lab from field data. Save report timestamp, tested URL, device profile, and available LCP/INP/CLS.
- Functionality: username input, URL input, community discovery, cancellation, question submission, source copying, guide links.
- Content: queries with impressions but weak click-through; unanswered reader needs; inaccurate archive/retention claims.
- Privacy: never export investigated usernames, question text, job identifiers, or push endpoints into acquisition analytics.

The `SEO production health` GitHub workflow runs daily at approximately 00:17 UTC and can also be started manually. It is read-only: it audits sitemap entries, `lastmod`, unique metadata, canonicals, structured data, links, compression/caching, noindex behavior, both Render alias controls, and the IndexNow key. It never scans an account, invokes an LLM, or submits URLs. GitHub schedules can be delayed; a missed scheduled run is not proof that production failed.

## Acquisition and conversion

Search Console measures search acquisition without adding client tracking. Conversion measurement is not implemented yet; if added, count generic events such as search_started, history_ready, and reply_copied without account/question content. Obtain appropriate analytics authorization and disclose processing before enabling an external service. Do not claim conversion improvements without comparable baseline data.

## Week-end evidence

Record deployed commit, live endpoint audit, test results, performance reports, Search Console verification/submission evidence, and any remaining access dependencies. Evaluate rankings over subsequent weeks rather than promising a one-week outcome.
