# SEO release evidence and remaining work

## Verified releases

- 31adf0a: foundational metadata, readable initial HTML, four static guides, robots/sitemap, API noindex, gzip, safe cache policies, follow-up question fix. Render deployment dep-dam82kp7lnhs73cddhgg verified live.
- 7ca9053: unused IBM Plex request removed; Inter moved from CSS import into preconnected HTML head; WebSite name markup; expanded production audit. Deployment dep-dam8489srm7s73ctj0l0 verified live with matching commit. Homepage source confirms Inter and WebSite markup, with unused Plex absent.

## Production observations: 18 September 2026

- Homepage and four guides pass HTTP/HTML audit: 200, one H1, unique title/description, self-canonical, social URL, links, assets, sitemap, job noindex and real 404s.
- Live hashed assets verified gzip with public one-year immutable caching.
- http://reddit-pi.live/ and https://www.reddit-pi.live/ return 301 to https://reddit-pi.live/.
- API and static Render origins return 200 with canonical referencing the custom domain. They remain functional aliases, not additional intended sitemap hosts.
- 94 offline backend tests and 17 frontend tests pass. Build passes; lint has only existing RunIntegrityStrip fast-refresh warning.

## Limits and missing evidence

- Browser runtime connection fails on this Windows environment; no visual mobile/browser pass claimed.
- PageSpeed API returned HTTP 429; no Lighthouse, LCP, INP or CLS pass claimed.
- Search Console ownership, sitemap submission, index selection and traffic baseline need authorized Google access. Render credentials do not provide it.
- Search ranking changes need observation over subsequent weeks. No traffic, CTR or conversion gain claimed.
- Three-day cache reuse is not automatic deletion. Methodology guide discloses missing scheduled purge and job-link access limits.

## Next decisions and week-end checks

1. Verify the latest deployed commit and rerun python scripts/audit_seo.py.
2. Connect authorized Search Console access; verify domain ownership and submit sitemap. Preserve unrelated DNS records.
3. Obtain mobile visual and PageSpeed evidence; optimize based on measured bottlenecks rather than score speculation.
4. Use real query/impression data to prioritize guide improvements. Candidate questions: missing history, fresh versus cached results, and choosing relevant community scope. Add content only where it resolves a distinct reader need.
5. Compare equal acquisition windows, annotate release dates, and verify job results stay excluded. Do not publish username dossiers as SEO landing pages or export searched account data into analytics.

The full week-long project remains active; this is release evidence, not a completion certificate.
