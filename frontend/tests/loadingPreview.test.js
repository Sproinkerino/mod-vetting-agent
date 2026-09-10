import test from 'node:test';
import assert from 'node:assert/strict';
import { loadingActivity } from '../src/lib/loadingPreview.js';

test('shows a bounded mixture of posts and comments while analysis runs', () => {
  const activity_preview = [
    { id: 'post', type: 'post', title: 'A post', body: 'Post body' },
    ...Array.from({ length: 8 }, (_, index) => ({ id: String(index), type: 'comment', body: `comment ${index}` })),
  ];
  assert.deepEqual(loadingActivity({ activity_preview }).map((item) => item.id), ['post', '0', '1', '2', '3', '4']);
});

test('drops unsupported or empty activity entries', () => {
  assert.deepEqual(loadingActivity({ activity_preview: [{ type: 'post', title: 'Kept' }, { type: 'post' }, { type: 'message', body: 'Dropped' }] }), [{ type: 'post', title: 'Kept' }]);
});
