import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { JSDOM } from 'jsdom';
import { buildGuides, guides } from '../scripts/build-guides.mjs';

test('guides have unique crawlable metadata, valid links and accessible semantics', async () => {
  const folder = await mkdtemp(join(tmpdir(), 'reddit-pi-seo-'));
  const titles = new Set();
  const descriptions = new Set();
  try {
    await buildGuides(folder);
    const sitemap = await readFile(join(folder, 'sitemap.xml'), 'utf8');
    assert.equal(guides.length, 6);
    assert.equal((sitemap.match(/<url>/g) || []).length, guides.length + 1);
    assert.equal((sitemap.match(/<lastmod>2026-09-19<\/lastmod>/g) || []).length, guides.length + 1);
    for (const guide of guides) {
      const url = `https://reddit-pi.live/guides/${guide.slug}/`;
      const html = await readFile(join(folder, 'guides', guide.slug, 'index.html'), 'utf8');
      const dom = new JSDOM(html, { url, runScripts: 'outside-only' });
      const doc = dom.window.document;
      assert.equal(doc.querySelectorAll('h1').length, 1);
      assert.equal(doc.querySelector('link[rel="canonical"]').href, url);
      assert.equal(doc.querySelector('meta[property="og:url"]').content, url);
      titles.add(doc.title);
      descriptions.add(doc.querySelector('meta[name="description"]').content);
      assert.ok(doc.querySelector('article').textContent.length > 1500);
      assert.ok(sitemap.includes(`<loc>${url}</loc>`));
      for (const link of doc.querySelectorAll('a')) {
        assert.ok(['/', ...guides.map((g) => `/guides/${g.slug}/`)].includes(new URL(link.href).pathname));
      }
      const graph = JSON.parse(doc.querySelector('script[type="application/ld+json"]').textContent);
      const breadcrumbs = graph['@graph'].find((item) => item['@type'] === 'BreadcrumbList');
      const article = graph['@graph'].find((item) => item['@type'] === 'Article');
      assert.equal(breadcrumbs.itemListElement[1].item, url);
      assert.equal(article.headline, guide.title);
      assert.equal(article.description, guide.description);
      assert.equal(article.dateModified, '2026-09-19');
      assert.equal(doc.querySelector('time').dateTime, article.dateModified);
      const axeSource = await readFile(new URL('../node_modules/axe-core/axe.min.js', import.meta.url), 'utf8');
      dom.window.eval(axeSource);
      const result = await dom.window.axe.run(doc, {
        runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] },
        rules: { 'color-contrast': { enabled: false } },
      });
      assert.deepEqual(Array.from(result.violations, (v) => v.id), []);
      dom.window.close();
    }
    assert.equal(titles.size, guides.length);
    assert.equal(descriptions.size, guides.length);
  } finally {
    await rm(folder, { recursive: true, force: true });
  }
});
