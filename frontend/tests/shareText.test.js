import test from 'node:test';
import assert from 'node:assert/strict';
import { buildRedditShareText, redditBlockquote } from '../src/lib/shareText.js';

test('prefixes every line so multiline text stays quoted on Reddit mobile', () => {
  assert.equal(redditBlockquote('first line\n\nsecond line'), '> first line\n>\n> second line');
});

test('truncates copied receipts to 50 characters', () => {
  assert.equal(redditBlockquote('a'.repeat(55)), `> ${'a'.repeat(50)}...`);
});

test('builds opener, quote-source pairs, closing, and app link in paste order', () => {
  const text = buildRedditShareText({
    sources: [{ body: 'first quote', permalink: 'https://reddit.com/one' }, { body: 'second quote', permalink: 'https://reddit.com/two' }],
    opener: 'You keep contradicting yourself.',
    answer: 'That is the final comment.',
    origin: 'https://example.com',
  });
  assert.equal(text, 'You keep contradicting yourself.\n\n> first quote\n[Source](https://reddit.com/one)\n\n> second quote\n[Source](https://reddit.com/two)\n\nThat is the final comment.\n\n[reddit-pi](https://example.com)');
});
