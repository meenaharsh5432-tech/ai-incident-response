'use strict';

/**
 * Standalone factory for Express error middleware.
 * Useful when you want the middleware object separate from the reporter.
 *
 * Usage:
 *   const { createErrorMiddleware } = require('incident-reporter/middleware');
 *   app.use(createErrorMiddleware(reporter));
 */
function createErrorMiddleware(reporter) {
  return function incidentReporterMiddleware(err, req, res, next) {
    try {
      reporter.captureError(err, {
        path: req.path || req.url,
        method: req.method,
        user_id: (req.user && req.user.id != null) ? String(req.user.id) : undefined,
        query: req.query,
      });
    } catch (_) {}
    next(err);
  };
}

/**
 * Wraps an async Express route handler so unhandled rejections are forwarded
 * to Express's error pipeline (and therefore to the incident reporter).
 *
 * Usage:
 *   app.get('/route', asyncWrapper(async (req, res) => { ... }))
 */
function asyncWrapper(fn) {
  return function asyncRouteWrapper(req, res, next) {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}

module.exports = { createErrorMiddleware, asyncWrapper };
