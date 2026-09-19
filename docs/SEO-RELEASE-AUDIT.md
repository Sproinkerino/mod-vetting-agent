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

- Chrome DevTools mobile emulation and local Lighthouse provide lab evidence, not Chrome UX Report field data. PageSpeed Insights continues to return HTTP 429, so no field Core Web Vitals claim is made.
- Search Console ownership, sitemap submission, index selection and traffic baseline need authorized Google access. Render credentials do not provide it.
- A public Google search check on 19 September 2026 returned no indexed `reddit-pi.live` pages. This is discovery evidence, not a substitute for Search Console's authoritative Indexing report.
- Search ranking changes need observation over subsequent weeks. No traffic, CTR or conversion gain claimed.
- Three-day cache reuse is not automatic deletion. Methodology guide discloses missing scheduled purge and job-link access limits.

## Next decisions and week-end checks

1. Verify the latest deployed commit and rerun python scripts/audit_seo.py.
2. Connect authorized Search Console access; verify domain ownership and submit sitemap. Preserve unrelated DNS records.
3. Obtain mobile visual and PageSpeed evidence; optimize based on measured bottlenecks rather than score speculation.
4. Use real query/impression data to prioritize guide improvements. Candidate questions: missing history, fresh versus cached results, and choosing relevant community scope. Add content only where it resolves a distinct reader need.
5. Compare equal acquisition windows, annotate release dates, and verify job results stay excluded. Do not publish username dossiers as SEO landing pages or export searched account data into analytics.

## Production recheck: 19 September 2026

- Commit `cbafd57` deployed live as Render deployment `dep-dan4877avr4c73a3e0kg`.
- `https://reddit-pi.live/`, `robots.txt`, the seven-URL sitemap, and all six guides return 200. The production crawler audit passes every status, HTML, canonical, description, H1, indexability, internal-link, uniqueness and social-URL check.
- HTTP and `www` permanently redirect to `https://reddit-pi.live/`.
- The API service alias permanently redirects `/` and `/guides/*` to the canonical host while preserving query strings; API methods and `/health` remain available and excluded from indexing.
- The separate static-service alias has no custom domains. Render header rule `hdr-dan49sajnfac73fah5c0` applies `X-Robots-Tag: noindex, nofollow` to `/*`, preventing the functional alias from competing with the canonical site. The canonical domain does not receive this header.
- A nonexistent guide returns a real 404 with `X-Robots-Tag: noindex, nofollow`. The production JavaScript asset is gzip-compressed and carries one-year immutable caching.
- IndexNow key ownership was verified live and the seven canonical sitemap URLs were submitted once on 19 September 2026; `api.indexnow.org` returned HTTP 202. This confirms receipt only, not crawling, indexing, or ranking. The submitter rejects non-HTTPS hosts, query strings, fragments, and paths outside `/` or `/guides/`.

The full week-long project remains active; this is release evidence, not a completion certificate.

## Mobile rendering correction: 19 September 2026

- A true Chrome device-emulation audit found the centered homepage grid using its minimum-content width. At a 390px viewport the document expanded to 481px, clipping the headline and search controls.
- The local fix gives the home grid a shrinkable `minmax(0, 1fr)` track, constrains the hero and form descendants, and preserves intentional horizontal scrolling only inside the popular-subreddit strip.
- Chrome measurements now show document width exactly matching viewport width at 320px, 360px, and 390px. Hero, form, and discovery controls remain fully inside each viewport; the chip strip remains independently scrollable.
- A 390px visual screenshot was inspected after the change. The headline, explanation, search button, community discovery control, selector, helper copy, and trust row are no longer clipped.
- The production build succeeds, all 19 frontend tests pass, and lint retains only the pre-existing `RunIntegrityStrip` Fast Refresh warning. Production deployment verification is still required before this item is recorded as live.
