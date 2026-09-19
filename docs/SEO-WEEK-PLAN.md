# reddit-pi SEO improvement week

## Objective

Improve search discoverability through useful original content, crawlability, mobile performance, and measurement. Preserve the search workflow. Never index account dossiers, fabricate testimonials or search volume, buy links, or promise rankings.

## Baseline: 18 September 2026

Live homepage returns 200 but initially contains only an empty React root. Source lacks canonical/social tags, robots, and sitemap. Search Console access, indexing status, traffic, and field Core Web Vitals are unverified.

## Seven-day delivery plan

1. Technical foundation: live audit, metadata, visible HTML, sitemap, robots, noindex analysis results, regression tests.
2. Query research and architecture: relevant search intents; linked original guides for history search, subreddit filters, quote verification.
3. Trust: actual archive coverage, AI limits, methodology, privacy, responsible use.
4. Performance: measure production and bundle; optimize critical assets/fonts; check mobile/accessibility regressions.
5. Measurement: Search Console setup with authorized access; submit sitemap; inspect URLs; acquisition/conversion baseline without logging investigated usernames or questions.
6. Release: build tracked artifacts; test crawlability, links, metadata; deploy and verify live responses.
7. Follow-up: check available crawl/index evidence; repair failures; monitoring checklist and prioritized content backlog. Search ranking effects may take weeks or longer.

## Acceptance gates

- Intended landing pages return 200 with unique metadata, canonical, useful visible HTML, internal links, and sitemap entry.
- Unknown URLs return real 404s. API/job-resume responses carry noindex; robots must not prevent crawlers reading that directive.
- No indexed account dossiers or unsupported affiliation/coverage claims.
- Existing tests and mobile accessibility pass; performance evidence includes measurement method and limits.
- Production matches tested release. Search Console/submission claims require actual access evidence.
- Final audit distinguishes verified deliverables from access needs and delayed search signals.

## Progress

Initial live/source audit complete. Foundation and three original static guides implemented locally. Guide navigation follows frontend-component-build semantic links, 44px targets, keyboard focus and automated accessibility checks. Static guides require no JavaScript or external fonts.

Search-intent research found recurring requests to search account comments and filter them by subreddit. These observations inform topic selection only; no search-volume or competition estimates are claimed. Google’s people-first content and title guidance inform descriptive headings and original, implementation-verified instructions.

Build baseline: main JS 243.65 kB / 78.96 kB gzip; CSS 26.02 kB / 5.87 kB gzip. These are build sizes, not field performance measurements. Public archive coverage and live availability remain explicitly qualified.

Methodology/data guide now explains archive source, external AI processing, incomplete coverage, opaque job-link access, optional push handling, and the distinction between cache expiry and deletion. Verified source has no scheduled report/checkpoint purge. Delivery adds gzip, immutable hashed-asset caching, HTML revalidation, and no-store for jobs. Fixed an existing follow-up question payload ReferenceError and added a regression test.

Measurement setup and privacy-preserving operational checks are documented in SEO-MEASUREMENT.md. Not deployed yet. Remaining: browser/field performance measurements, Search Console access and submission, release verification and follow-up.

## Production release evidence

Commit 31adf0a deployed live through Render deployment dep-dam82kp7lnhs73cddhgg. Production audit passed for homepage plus four guides: statuses, canonical/description/headings, internal links, sitemap/robots, noindex job responses and true 404s. Live hashed JS returns gzip and immutable one-year cache headers. 93 backend and 17 frontend tests passed. Browser runtime failed to connect; PageSpeed API returned 429, so visual and Core Web Vitals evidence remains missing. Search Console needs authorized access.

Follow-up performance inspection found unused IBM Plex requests in HTML and actual Inter font loaded through CSS @import. Moving Inter to the preconnected HTML head removes the chained font stylesheet discovery and unused font-family request without changing typography. Added truthful WebSite brand markup; stronger auditor checks unique metadata, social canonical and local asset availability/compression/cache.

Day-two content expansion (19 September 2026): added original guides for missing archive activity and cached-versus-fresh searches, addressing two distinct product questions without creating username dossier pages. All six guides now expose Article plus Breadcrumb structured data, visible and machine-readable review dates, sitemap `lastmod`, canonical metadata, and crawlable homepage navigation. Automated tests validate all seven intended public URLs, unique metadata, internal links, structured data, sitemap coverage, and WCAG A/AA semantics. Google Search documentation was rechecked before implementation; FAQ rich-result markup was deliberately not added because these are editorial guides rather than a supported FAQ use case.
