import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { JSDOM } from 'jsdom';

test('static-host resumed jobs receive noindex without hiding the public homepage', async () => {
  const html = await readFile(new URL('../index.html', import.meta.url), 'utf8');
  for (const [query, expected] of [['', null], ['?utm_source=test', null], ['?job=example', 'noindex, nofollow'], ['?job=', 'noindex, nofollow']]) {
    const dom = new JSDOM(html, { url: `https://reddit-pi.live/${query}`, runScripts: 'dangerously' });
    assert.equal(dom.window.document.querySelector('meta[name="robots"]')?.content ?? null, expected);
    dom.window.close();
  }
});
