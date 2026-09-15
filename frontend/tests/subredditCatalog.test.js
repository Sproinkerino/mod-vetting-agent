import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const catalogUrl = new URL('../src/data/popularSubreddits.json', import.meta.url);

test('bundled subreddit directory contains 1,000 unique valid names', async () => {
  const names = JSON.parse(await readFile(catalogUrl, 'utf8'));
  assert.equal(names.length, 1000);
  assert.equal(new Set(names.map((name) => name.toLowerCase())).size, 1000);
  assert.ok(names.every((name) => /^[A-Za-z0-9_]{2,21}$/.test(name)));
  assert.ok(names.includes('masterduel'));
  assert.ok(names.includes('singapore'));
});