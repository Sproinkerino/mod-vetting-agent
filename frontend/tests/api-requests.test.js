import test from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';

test('a follow-up question reaches the API with scope and source count', async () => {
  const server = await createServer({ root: fileURLToPath(new URL('..', import.meta.url)),
    server: { middlewareMode: true }, appType: 'custom' });
  const originalFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, payload: JSON.parse(options.body) });
    return { ok: true, json: async () => ({ answer: 'Supported answer', sources: [] }) };
  };
  try {
    const { askArchive, startJob } = await server.ssrLoadModule('/src/lib/api.js');
    const report = { applicant: { username: 'example' }, activity: [] };
    assert.equal((await askArchive('job123', 'What did they say?', report, 2, ['comics'])).answer, 'Supported answer');
    assert.ok(calls[0].url.endsWith('/jobs/job123/ask'));
    assert.deepEqual(calls[0].payload, { question: 'What did they say?', username: 'example', activity: [], source_count: 2, subreddits: ['comics'] });
    await startJob('example', [], true);
    assert.equal(calls[1].payload.discover_communities, true);
  } finally {
    globalThis.fetch = originalFetch;
    await server.close();
  }
});
