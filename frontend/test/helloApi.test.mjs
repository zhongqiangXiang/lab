import assert from 'node:assert/strict';
import test from 'node:test';
import { fetchHello } from '../.tmp/test-dist/helloApi.js';

test('fetchHello returns the backend message', async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/hello');
    assert.ok(options.signal instanceof AbortSignal);

    return new Response(JSON.stringify({ message: 'hello' }), {
      headers: { 'content-type': 'application/json' },
      status: 200,
    });
  };

  try {
    assert.deepEqual(await fetchHello(new AbortController().signal), { message: 'hello' });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchHello reports non-2xx backend responses', async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => new Response('Not found', { status: 404 });

  try {
    await assert.rejects(fetchHello(), /Backend returned HTTP 404/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchHello rejects malformed backend payloads', async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () =>
    new Response(JSON.stringify({ value: 'hello' }), {
      headers: { 'content-type': 'application/json' },
      status: 200,
    });

  try {
    await assert.rejects(fetchHello(), /missing a message/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
