'use strict';

/**
 * Example Express app — zero-instrumentation error capture.
 *
 * Run:  node index.js
 * Then: curl http://localhost:8003/
 *       curl http://localhost:8003/json-parse-error
 *       curl http://localhost:8003/db-connection
 *       curl http://localhost:8003/auth-expired
 *
 * Every unhandled error auto-appears in the incident dashboard.
 */

const path = require('path');
const express = require('express');

// Resolve the SDK from the project root
const { IncidentReporter } = require(path.join(__dirname, '..', '..', 'incident-reporter-node'));
const { asyncWrapper } = require(path.join(__dirname, '..', '..', 'incident-reporter-node', 'middleware'));

const app = express();
app.use(express.json());

const reporter = new IncidentReporter({
  apiUrl: process.env.INCIDENT_API_URL || 'http://localhost:8001',
  serviceName: 'express-example',
  environment: 'dev',
  apiKey: process.env.INCIDENT_API_KEY || undefined,
});


// ─── Routes ──────────────────────────────────────────────────────────────────

app.get('/', (req, res) => {
  res.json({ status: 'ok', service: 'express-example' });
});

app.get('/json-parse-error', (req, res) => {
  // Simulate: corrupt response from upstream service
  const corrupt = '{"user": "alice", "token": }';  // invalid JSON
  const data = JSON.parse(corrupt);
  res.json(data);
});

// asyncWrapper forwards promise rejections to Express error pipeline
app.get('/db-connection', asyncWrapper(async (req, res) => {
  // Simulate: MongoDB connection refused
  throw new Error('ECONNREFUSED: MongoDB connection refused at localhost:27017');
}));

app.get('/auth-expired', (req, res) => {
  // Simulate: JWT expiry not caught by auth middleware
  const token = req.headers.authorization;
  if (!token) {
    throw new Error('TokenExpiredError: JWT expired at 2024-01-01T00:00:00.000Z');
  }
  res.json({ user: 'authenticated' });
});


// ─── Error middleware (must be AFTER all routes) ──────────────────────────────

// One line: captures all Express errors + passes them down the error chain
app.use(reporter.middleware());

// Final handler — returns JSON 500 to the client
app.use((err, req, res, next) => { // eslint-disable-line no-unused-vars
  res.status(500).json({ error: err.message || 'Internal server error' });
});


// ─── Start ────────────────────────────────────────────────────────────────────

const PORT = process.env.PORT || 9003;
app.listen(PORT, () => {
  console.log(`Express example running on http://localhost:${PORT}`);
});

module.exports = app;
