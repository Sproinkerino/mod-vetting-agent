import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

// Original product documentation, emitted as real HTML for readers and crawlers.
export const guides = [
  {
    slug: 'methodology-and-data', title: 'How reddit-pi works: sources, AI, and data retention',
    description: 'Understand reddit-pi’s public archive sources, evidence review, AI limitations, three-day cache, and current data-retention behavior.',
    sections: [
      ['Independent public-history research', 'reddit-pi is an independent tool, not an official Reddit service. It retrieves available public posts and comments through the Arctic Shift archive API. Reddit share links may be resolved through Reddit to identify the linked item. Archive coverage and freshness vary; the tool cannot guarantee a complete history or retrieve private messages.'],
      ['What the AI reviews', 'A scan fetches a bounded history and applies any selected subreddit scope before analysis. The pipeline screens items, reviews candidate evidence more deeply, and checks quotes against supplied text. Follow-up questions use batch evidence review and a final evidence-selection step before drafting a cited reply. Candidate review can use shortened text, so material outside the reviewed excerpt may be missed.'],
      ['External AI processing', 'Analysis sends relevant public activity and your questions to the configured AI provider. The application supports DeepSeek, OpenRouter, and Anthropic; deployment configuration determines which is used. These services have their own processing policies. Do not enter confidential information in a question merely because the Reddit history itself is public.'],
      ['Cache lifetime is not deletion', 'Completed reports can be reused for three days when the search scope and analysis contract match. After that interval the cache entry is no longer eligible for reuse. The current implementation does not automatically delete expired report rows or analysis checkpoints from its SQLite database. In-memory jobs and toxic-compilation caches can disappear when the server restarts. Hosting storage behavior may affect persistence.'],
      ['Access and privacy limits', 'A job link contains an opaque identifier, not a login-protected account. Anyone with a working job identifier may be able to read that job through the API while it remains available. Analysis responses and job-resume pages request exclusion from search indexes; noindex is not an access-control mechanism. Server hosting and external providers may maintain operational logs.'],
      ['Optional notifications', 'If you choose Notify me and allow browser notifications, the app stores the push subscription in server memory for that job. It removes the subscription when sending the terminal job alert. The notification uses generic text rather than naming the investigated account. Delivery is best-effort and subscriptions are not a durable queue across restarts.'],
      ['Interpretation needs a reader', 'An exact textual match verifies that an excerpt exists in the supplied archive, not that a claim is true in the real world. Check authorship, dates, surrounding context, and the original source. Behavioral signals describe selected evidence, not medical diagnoses or reliable measurements of a person’s overall character. Do not use the tool to expose private identities or organize harassment.'],
    ],
  },
  {
    slug: 'reddit-user-history', title: 'How to search Reddit user history',
    description: 'Explore a Reddit account’s public posts and comments, ask focused questions, and check sources while understanding archive limitations.',
    sections: [
      ['Start with the account or the conversation', 'Enter a Reddit username, with or without u/, on the reddit-pi homepage. You can also paste a full reddit.com post or comment URL to investigate the author behind that conversation. Check that you selected the intended account before starting; similarly named accounts are not interchangeable.'],
      ['Find the communities worth reading', 'Use “Find their top subreddit first” to see where the account is active in the fetched history before running AI analysis. These counts describe the items available to this scan, not a complete lifetime ranking. Choose a relevant community or leave the selection empty to consider all fetched communities.'],
      ['Read the history before accepting the answer', 'Public activity appears while deeper analysis runs. Once the case is ready, ask a concrete question such as “What have they said about learning this game?” Read the returned raw text and open the source links. Posts include the author’s title and body; another person’s thread title is context, not a statement made by the commenter.'],
      ['What a search cannot prove', 'reddit-pi uses public archive data, which may be incomplete or out of date. It does not provide access to private messages or private communities. No results does not prove that the person never discussed a topic. A few comments cannot establish someone’s identity, character, or current circumstances.'],
      ['Reuse and correct your search', 'Completed scans can be reused from a three-day cache without repeating the analysis. Cancel a running scan if the username or community is wrong. A cached scan may not include newly posted activity; check dates and the original Reddit context before quoting it.'],
    ],
  },
  {
    slug: 'filter-reddit-history-by-subreddit', title: 'Filter Reddit user history by subreddit',
    description: 'Choose communities before a Reddit history scan, narrow your question after analysis, and recover when a selected subreddit has no available activity.',
    sections: [
      ['Choose a useful scope before analysis', 'Type a community name into the subreddit picker and select a suggestion. The bundled popular-community list is a starting point, not a complete directory of Reddit. Selecting communities limits the fetched items sent through AI analysis. An empty selection means all fetched communities, not every comment ever written.'],
      ['Discover where the account actually posts', 'If you do not know which community to choose, use “Find their top subreddit first.” The app counts public items in the fetched history without running the deeper AI analysis. Select a suggested community that is relevant to your question rather than assuming the busiest one is always the right one.'],
      ['Adjust the scope after the case is ready', 'The completed case has a community filter for visible evidence, signals, and the activity archive. Changing that view does not rerun the original analysis. The question box also lets you select which analyzed communities its evidence review should use. A filter cannot add a community that was excluded from the original scan.'],
      ['Recover from an empty selection', 'When no public items are found in your chosen communities, the app suggests communities represented in the fetched history. Try a relevant suggestion or start a new search with a broader scope. An empty result means nothing was available in this scan; it is not proof of nonparticipation.'],
      ['Compare like with like', 'A game discussion and a workplace discussion can have very different norms. Read the original thread and dates before comparing wording. Community counts and behavioral signals apply to the selected evidence, not to the account’s entire life or offline personality.'],
    ],
  },
  {
    slug: 'verify-reddit-quotes', title: 'Verify Reddit quotes before sharing a reply',
    description: 'Check authorship, dates, surrounding context, and source links before using Reddit quotes in a cited reply.',
    sections: [
      ['Ask a question that can be checked', 'Use a specific request such as “Find their own comments about starting this deck” rather than “Prove they are a liar.” The evidence review interprets meaning rather than relying only on exact word matches, but it can still miss relevant items or misunderstand context. No supported receipt is a valid result.'],
      ['Check who wrote the words', 'For a post, the title and body belong to its author. For a comment, the submission title may have been written by someone else. A quoted insult, reported experience, or criticism of racism should not be attributed as the commenter’s own endorsement. Read the whole authored text.'],
      ['Open the original source and check dates', 'Follow each Source link and compare the surrounding conversation. Circumstances can change: a statement about unemployment last year does not disprove a claim about employment today. Jokes, game terminology, hypothetical examples, and quotations may also change what the words mean. If the source is unavailable, describe that uncertainty rather than presenting it as verified live evidence.'],
      ['Keep excerpts short without changing their meaning', 'Copy-ready replies use focused excerpts and source links. Expand the raw text before copying. Do not omit a negation, qualification, or later correction merely to make an accusation stronger. Use the source-count control when a single quote is insufficient; more quotes are not automatically better evidence.'],
      ['Separate evidence from interpretation', 'AI-generated reply wording is a draft, not an independent fact-check. Every factual sentence should be supported by the selected receipts. Edit or discard a reply that overstates them. Do not use public-history research to expose private identities, organize harassment, or make unsupported character diagnoses.'],
    ],
  },
  {
    slug: 'why-reddit-history-is-missing', title: 'Why Reddit user history can be missing',
    description: 'Understand why public Reddit posts or comments may be absent from a history search, and what you can check before drawing a conclusion.',
    sections: [
      ['A public archive is not a complete account record', 'reddit-pi searches available public archive data; it does not read a private Reddit account database. A post or comment may be unavailable because it was never archived, was removed before capture, is too recent, belongs to a private community, or falls outside the bounded history fetched for the scan. Missing text is therefore an absence of evidence, not evidence that the activity never existed.'],
      ['Check that you searched the intended account', 'Confirm the spelling, capitalization, underscores, and any digits in the username. If you started from a Reddit link, open the original conversation and verify which author the app identified. Deleted authors and similarly named accounts can make attribution impossible or misleading.'],
      ['Remove an overly narrow community filter', 'A subreddit filter only keeps available activity from the selected communities. If that scope is empty, review the suggested communities found in the fetched history or start a broader search without a subreddit selection. A filter cannot reveal content that was absent from the underlying archive.'],
      ['Compare the dates and try a fresh scan later', 'A reused report can be up to three days old. Recent activity may not appear in that cached result, and a fresh scan may still lag behind Reddit because archive ingestion is not instantaneous. Check the source date on Reddit and avoid presenting a timing gap as a contradiction.'],
      ['Use another source for high-stakes verification', 'Open the account on Reddit, search the relevant community, and retain the original permalink when it is available. For employment, identity, safety, legal, or other consequential claims, public comment history alone is not a reliable verification method. Describe the limitation directly instead of filling the gap with an assumption.'],
    ],
  },
  {
    slug: 'cached-vs-fresh-reddit-search', title: 'Cached vs fresh Reddit history searches',
    description: 'Learn when reddit-pi reuses a three-day report, what a cached result contains, and when a different scope creates a new analysis.',
    sections: [
      ['Why reddit-pi reuses completed analysis', 'AI review can take time and incur provider costs. When the same account, subreddit scope, and analysis contract are requested again within three days, reddit-pi can reuse the completed report instead of repeating the model calls. Reuse reduces waiting time and avoids charging for identical analysis.'],
      ['What stays the same in a cached report', 'A reused report reflects the public activity and analysis captured by the earlier run. It does not silently append comments posted afterward. The evidence, scores, and generated summary should be read as a snapshot, with original dates and source links checked before use.'],
      ['What creates a different analysis', 'Changing the selected subreddit scope changes the scan input and therefore its cache identity. Application updates that change the analysis contract can also invalidate reuse. Adjusting only the completed report view does not rerun the model or add communities excluded at the beginning.'],
      ['Questions and compiled receipts are separate calls', 'Follow-up questions and toxic-receipt compilation evaluate the available archive for that job. They can make additional AI calls even when the main report was reused. Their answers remain limited by the activity that was fetched and by the selected question scope.'],
      ['Choose accuracy over apparent certainty', 'Use cached results for quick review when the snapshot is recent enough for your purpose. If timing matters, compare the source dates with current Reddit activity and state that archive coverage may lag. Neither a cached nor a fresh scan proves that it contains every public statement by an account.'],
    ],
  },
];

const esc = (value) => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const links = guides.map((g) => `<a href="/guides/${g.slug}/">${esc(g.title)}</a>`).join('');
const css = `:root{--ink:#26374c;--muted:#56677a;--blue:#1764ad;--bg:#eef3f9;--card:#fff;--line:#d7e2ed}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.7 system-ui,sans-serif}header,main,footer{max-width:820px;margin:auto;padding:20px}header{display:flex;justify-content:space-between;align-items:center;gap:16px}main{background:var(--card);border:1px solid var(--line);border-radius:12px}h1{font-size:clamp(26px,5vw,38px);line-height:1.2}h2{font-size:23px;line-height:1.35;margin-top:30px}a{color:var(--blue);text-underline-offset:3px}header a,nav a,.cta{display:inline-flex;align-items:center;min-height:44px;padding:8px 0}nav{display:grid;gap:8px}a:hover{color:var(--ink)}a:focus-visible{outline:3px solid var(--blue);outline-offset:4px}.summary{color:var(--muted)}.skip{position:absolute;left:16px;top:-100px}.skip:focus{top:0;background:var(--card);padding:8px}footer{font-size:14px;color:var(--muted)}@media(max-width:860px){main{margin:0 12px}}`;

export async function buildGuides(outDir) {
  const urls = ['https://reddit-pi.live/'];
  const reviewed = '2026-09-19';
  for (const guide of guides) {
    const url = `https://reddit-pi.live/guides/${guide.slug}/`;
    urls.push(url);
    const breadcrumbs = { '@type': 'BreadcrumbList', itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'reddit-pi', item: 'https://reddit-pi.live/' },
      { '@type': 'ListItem', position: 2, name: guide.title, item: url },
    ] };
    const article = { '@type': 'Article', headline: guide.title, description: guide.description, url,
      datePublished: '2026-09-18', dateModified: reviewed,
      author: { '@type': 'Organization', name: 'reddit-pi' },
      publisher: { '@type': 'Organization', name: 'reddit-pi', url: 'https://reddit-pi.live/' },
    };
    const structuredData = { '@context': 'https://schema.org', '@graph': [breadcrumbs, article] };
    const html = `<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${esc(guide.title)} | reddit-pi</title><meta name="description" content="${esc(guide.description)}"><link rel="canonical" href="${url}"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><meta property="og:type" content="article"><meta property="og:site_name" content="reddit-pi"><meta property="og:title" content="${esc(guide.title)}"><meta property="og:description" content="${esc(guide.description)}"><meta property="og:url" content="${url}"><meta property="article:modified_time" content="${reviewed}T00:00:00+08:00"><meta name="twitter:card" content="summary"><style>${css}</style><script type="application/ld+json">${JSON.stringify(structuredData)}</script></head><body><a class="skip" href="#main-content">Skip to content</a><header><a href="/" aria-label="reddit-pi home">reddit-pi</a><a href="/#reddit-target">Search public history</a></header><main id="main-content"><article><p class="summary">reddit-pi product guide · Reviewed <time datetime="${reviewed}">19 September 2026</time></p><h1>${esc(guide.title)}</h1><p class="summary">${esc(guide.description)}</p>${guide.sections.map(([heading, body]) => `<section><h2>${esc(heading)}</h2><p>${esc(body)}</p></section>`).join('')}<a class="cta" href="/">Try a public Reddit history search →</a></article><nav aria-label="Related guides"><h2>Related guides</h2>${links}</nav></main><footer>Independent tool; not affiliated with Reddit. Public archives can be incomplete. Verify original context before sharing a claim.</footer></body></html>`;
    const folder = resolve(outDir, 'guides', guide.slug);
    await mkdir(folder, { recursive: true });
    await writeFile(resolve(folder, 'index.html'), html);
  }
  await writeFile(resolve(outDir, 'sitemap.xml'), `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls.map((url) => `<url><loc>${url}</loc><lastmod>${reviewed}</lastmod></url>`).join('')}</urlset>`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  await buildGuides(fileURLToPath(new URL('../dist/', import.meta.url)));
}
