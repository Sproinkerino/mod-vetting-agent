import test from 'node:test';
import assert from 'node:assert/strict';
import { sourceExcerpt, sourceKind, sourceText } from '../src/lib/sourceContent.js';

test('formats a text post with its title and body', () => {
  const post = { type: 'post', title: 'Why this matters', body: 'A longer explanation.' };
  assert.equal(sourceText(post), 'Why this matters\nA longer explanation.');
  assert.equal(sourceExcerpt(post, 50), 'Why this matters A longer explanation.');
  assert.equal(sourceKind(post), 'Post');
});

test('does not duplicate a link post title stored as its body', () => {
  const post = { type: 'post', title: 'Linked article', body: 'Linked article' };
  assert.equal(sourceText(post), 'Linked article');
});

test('comments use their body rather than the surrounding post title', () => {
  const comment = { type: 'comment', title: 'Discussion title', body: 'The actual comment.' };
  assert.equal(sourceText(comment), 'The actual comment.');
  assert.equal(sourceKind(comment), 'Comment');
});
