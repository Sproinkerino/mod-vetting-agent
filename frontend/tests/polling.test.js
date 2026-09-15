import test from 'node:test';
import assert from 'node:assert/strict';
import { abortableDelay, throwIfAborted } from '../src/lib/polling.js';

test('an aborted investigation stops before another poll', async () => {
  const controller = new AbortController();
  const waiting = abortableDelay(10_000, controller.signal);
  controller.abort();
  await assert.rejects(waiting, (error) => error.name === 'AbortError');
});

test('an already-aborted investigation fails immediately', () => {
  const controller = new AbortController();
  controller.abort();
  assert.throws(() => throwIfAborted(controller.signal), (error) => error.name === 'AbortError');
});