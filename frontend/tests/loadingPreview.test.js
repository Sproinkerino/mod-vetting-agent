import test from 'node:test';
import assert from 'node:assert/strict';
import { loadingComments, previewComment } from '../src/lib/loadingPreview.js';

test('shows only bounded comments while analysis runs', () => {
  const activity_preview = [
    { id: 'post', type: 'post', body: 'title' },
    ...Array.from({ length: 8 }, (_, index) => ({ id: String(index), type: 'comment', body: `comment ${index}` })),
  ];
  assert.deepEqual(loadingComments({ activity_preview }).map((item) => item.id), ['0', '1', '2', '3', '4', '5']);
});

test('creates a compact readable loading preview', () => {
  assert.equal(previewComment(`  ${'a'.repeat(165)}  `), `${'a'.repeat(160)}…`);
});