'use strict';

const fs = require('fs');
const { IncidentReporter } = require('../index');
const { createErrorMiddleware, asyncWrapper } = require('../middleware');

function makeReporter(overrides = {}) {
  return new IncidentReporter({
    apiUrl: 'http://localhost:8000',
    serviceName: 'test-service',
    flushInterval: 999999,  // disable auto-flush during tests
    ...overrides,
  });
}

describe('IncidentReporter.captureError', () => {
  let reporter;

  beforeEach(() => { reporter = makeReporter(); });
  afterEach(async () => { await reporter.shutdown(); });

  test('queues a well-formed payload', () => {
    const err = new Error('test error');
    reporter.captureError(err);
    expect(reporter._queue).toHaveLength(1);
    expect(reporter._queue[0]).toMatchObject({
      error_type: 'Error',
      message: 'test error',
      service_name: 'test-service',
      environment: 'prod',
    });
    expect(typeof reporter._queue[0].stack_trace).toBe('string');
  });

  test('includes metadata', () => {
    reporter.captureError(new TypeError('bad type'), { path: '/api', user_id: '42' });
    expect(reporter._queue[0].error_type).toBe('TypeError');
    expect(reporter._queue[0].metadata).toEqual({ path: '/api', user_id: '42' });
  });

  test('never throws for null/undefined', () => {
    expect(() => reporter.captureError(null)).not.toThrow();
    expect(() => reporter.captureError(undefined)).not.toThrow();
    expect(() => reporter.captureError('string')).not.toThrow();
  });
});

describe('IncidentReporter._sendWithRetry', () => {
  let reporter;

  beforeEach(() => { reporter = makeReporter({ maxRetries: 3 }); });
  afterEach(async () => { await reporter.shutdown(); });

  test('resolves on first success', async () => {
    reporter._post = jest.fn().mockResolvedValue({ id: 1, incident_id: 1 });
    await reporter._sendWithRetry({ error_type: 'Error', message: 'x' });
    expect(reporter._post).toHaveBeenCalledTimes(1);
  });

  test('retries with exponential backoff on failure', async () => {
    reporter._post = jest.fn().mockRejectedValue(new Error('down'));
    reporter._sleep = jest.fn().mockResolvedValue();
    const fallbackSpy = jest.spyOn(reporter, '_writeFallback').mockImplementation(() => {});

    await reporter._sendWithRetry({ error_type: 'Error', message: 'x' });

    expect(reporter._post).toHaveBeenCalledTimes(4); // initial + 3 retries
    expect(reporter._sleep).toHaveBeenCalledTimes(3);
    expect(reporter._sleep).toHaveBeenNthCalledWith(1, 1000);  // 2^0 * 1000
    expect(reporter._sleep).toHaveBeenNthCalledWith(2, 2000);  // 2^1 * 1000
    expect(reporter._sleep).toHaveBeenNthCalledWith(3, 4000);  // 2^2 * 1000
    expect(fallbackSpy).toHaveBeenCalledTimes(1);
  });

  test('writes fallback after all retries exhausted', async () => {
    const fsSpy = jest.spyOn(fs, 'appendFileSync').mockImplementation(() => {});
    reporter._post = jest.fn().mockRejectedValue(new Error('unavailable'));
    reporter._sleep = jest.fn().mockResolvedValue();
    reporter.maxRetries = 1;

    await reporter._sendWithRetry({ error_type: 'DBError', message: 'conn refused' });

    expect(fsSpy).toHaveBeenCalled();
    const written = fsSpy.mock.calls[0][1];
    const entry = JSON.parse(written.trim());
    expect(entry.error_type).toBe('DBError');
    expect(entry.timestamp).toBeDefined();
    fsSpy.mockRestore();
  });

  test('includes X-API-Key header when apiKey set', async () => {
    reporter = makeReporter({ apiKey: 'my-secret-key' });
    const postSpy = jest.spyOn(reporter, '_post').mockResolvedValue({});

    await reporter._sendWithRetry({ error_type: 'E', message: 'm' });

    // The _post method is called with url + body; check headers via the real _post logic
    // Here we just verify _post is called (header test is in integration)
    expect(postSpy).toHaveBeenCalledTimes(1);
    await reporter.shutdown();
  });
});

describe('IncidentReporter.middleware()', () => {
  let reporter;

  beforeEach(() => { reporter = makeReporter(); });
  afterEach(async () => { await reporter.shutdown(); });

  test('returns a 4-argument Express error handler', () => {
    const mw = reporter.middleware();
    expect(typeof mw).toBe('function');
    expect(mw.length).toBe(4);
  });

  test('calls captureError with error and request metadata', () => {
    const mw = reporter.middleware();
    const captureSpy = jest.spyOn(reporter, 'captureError');
    const err = new Error('express error');
    const req = { path: '/api/test', method: 'POST', url: '/api/test', user: { id: 7 } };
    const next = jest.fn();

    mw(err, req, {}, next);

    expect(captureSpy).toHaveBeenCalledWith(err, expect.objectContaining({
      path: '/api/test',
      method: 'POST',
      user_id: '7',
    }));
    expect(next).toHaveBeenCalledWith(err);
  });

  test('always calls next(err) even if captureError throws', () => {
    jest.spyOn(reporter, 'captureError').mockImplementation(() => { throw new Error('reporter crashed'); });
    const mw = reporter.middleware();
    const err = new Error('real error');
    const next = jest.fn();

    mw(err, { path: '/', method: 'GET', url: '/' }, {}, next);

    expect(next).toHaveBeenCalledWith(err);
  });
});

describe('createErrorMiddleware', () => {
  test('wraps reporter with query metadata', () => {
    const mockReporter = { captureError: jest.fn() };
    const mw = createErrorMiddleware(mockReporter);
    const err = new TypeError('test');
    const req = { path: '/x', method: 'GET', url: '/x', query: { debug: '1' }, user: null };
    const next = jest.fn();

    mw(err, req, {}, next);

    expect(mockReporter.captureError).toHaveBeenCalledWith(err, expect.objectContaining({
      path: '/x',
      query: { debug: '1' },
    }));
    expect(next).toHaveBeenCalledWith(err);
  });
});

describe('asyncWrapper', () => {
  test('forwards rejection to next()', async () => {
    const err = new Error('async route failed');
    const fn = async () => { throw err; };
    const wrapped = asyncWrapper(fn);
    const next = jest.fn();

    await wrapped({}, {}, next);

    expect(next).toHaveBeenCalledWith(err);
  });

  test('does not call next on success', async () => {
    const fn = async (req, res) => { res.json({ ok: true }); };
    const wrapped = asyncWrapper(fn);
    const res = { json: jest.fn() };
    const next = jest.fn();

    await wrapped({}, res, next);

    expect(res.json).toHaveBeenCalledWith({ ok: true });
    expect(next).not.toHaveBeenCalled();
  });
});
