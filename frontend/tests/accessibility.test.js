import test from 'node:test';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import { JSDOM } from 'jsdom';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

test('new compilation and install controls have accessible semantics', async () => {
  const server = await createServer({
    root: fileURLToPath(new URL('..', import.meta.url)),
    server: { middlewareMode: true }, appType: 'custom',
  });
  try {
    const { default: Compilation } = await server.ssrLoadModule('/src/components/ToxicCompilation.jsx');
    const { default: LoadingOptions } = await server.ssrLoadModule('/src/components/LoadingOptions.jsx');
    const markup = renderToStaticMarkup(React.createElement('main', null,
      React.createElement(Compilation, {
        report: { applicant: { username: 'example' }, activity: [], api_job_id: 'example' },
        subreddits: [],
      }),
      React.createElement(LoadingOptions, { jobId: 'example' }),
    ));
    const dom = new JSDOM('<!doctype html><html lang="en"><head><title>reddit-pi accessibility</title></head><body>' + markup + '</body></html>');
    globalThis.window = dom.window;
    globalThis.document = dom.window.document;
    const { default: axe } = await import('axe-core');
    const results = await axe.run(dom.window.document, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] },
      rules: { 'color-contrast': { enabled: false } },
    });
    assert.deepEqual(results.violations.map((item) => item.id), []);
    const buttons = [...dom.window.document.querySelectorAll('button')];
    assert.ok(buttons.some((button) => button.textContent.includes('Compile Toxic Receipts')));
    assert.ok(buttons.some((button) => button.textContent.includes('Save to Home Screen')));
    assert.ok(buttons.every((button) => button.type === 'button'));
    dom.window.close();
  } finally {
    await server.close();
  }
});
