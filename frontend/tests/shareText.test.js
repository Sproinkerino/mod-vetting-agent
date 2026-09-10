import test from 'node:test';
import assert from 'node:assert/strict';
import { buildRedditShareText, redditBlockquote } from '../src/lib/shareText.js';

test('prefixes every line so multiline text stays quoted on Reddit mobile', () => {
  assert.equal(redditBlockquote('first line\n\nsecond line'), '> first line\n>\n> second line');
});

test('builds quotes, comeback, and linked sources in paste order', () => {
  const text = buildRedditShareText({
    sources: [{ body: 'first quote', permalink: 'https://reddit.com/one' }, { body: 'second quote', permalink: 'https://reddit.com/two' }],
    answer: 'That is the comeback.',
    origin: 'https://example.com',
  });
  assert.equal(text, '> first quote\n\n> second quote\n\nThat is the comeback.\n\n[Source 1](https://reddit.com/one)\n[Source 2](https://reddit.com/two)\n\nCheck a Redditor\'s public history: https://example.com');
});
