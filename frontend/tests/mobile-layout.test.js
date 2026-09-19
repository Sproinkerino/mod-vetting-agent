import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const cssUrl = new URL('../src/index.css', import.meta.url);

test('homepage grid can shrink to a mobile viewport', async () => {
  const css = await readFile(cssUrl, 'utf8');

  assert.match(css, /\.home\{width:100%;grid-template-columns:minmax\(0,1fr\)\}/);
  assert.match(css, /\.hero\{width:100%;max-width:720px;min-width:0;justify-self:center\}/);
  assert.match(css, /\.popular-subreddits\{min-width:0;max-width:100%\}/);
  assert.match(css, /\.discover-communities\{grid-template-columns:auto minmax\(0,1fr\) auto\}/);
});
