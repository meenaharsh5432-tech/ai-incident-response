'use strict';

const fs = require('fs');
const http = require('http');
const https = require('https');
const path = require('path');

class IncidentReporter {
  /**
   * @param {object} opts
   * @param {string} opts.apiUrl       - Base URL of the incident backend (e.g. "http://localhost:8000")
   * @param {string} opts.serviceName  - Name of this service
   * @param {string} [opts.environment]     - "prod" | "staging" | "dev"  (default: "prod")
   * @param {string|null} [opts.apiKey]     - X-API-Key for authenticated backends
   * @param {number} [opts.flushInterval]   - ms between auto-flushes (default: 5000)
   * @param {number} [opts.maxRetries]      - retries after initial failure (default: 3)
   * @param {string} [opts.fallbackLogPath] - local file written when API unreachable
   */
  constructor({
    apiUrl,
    serviceName,
    environment = 'prod',
    apiKey = null,
    flushInterval = 5000,
    maxRetries = 3,
    fallbackLogPath = 'incident_fallback.log',
  } = {}) {
    if (!apiUrl) throw new Error('apiUrl is required');
    if (!serviceName) throw new Error('serviceName is required');

    this.apiUrl = apiUrl.replace(/\/$/, '');
    this.serviceName = serviceName;
    this.environment = environment;
    this.apiKey = apiKey;
    this.maxRetries = maxRetries;
    this.fallbackLogPath = path.resolve(fallbackLogPath);

    this._queue = [];
    // unref() so the timer doesn't prevent Node.js from exiting
    this._timer = setInterval(() => this._flush(), flushInterval).unref();
  }

  /**
   * Capture an error and queue it for reporting.
   * Never throws — safe to call from any context.
   */
  captureError(error, metadata = {}) {
    try {
      const payload = {
        error_type: (error && error.constructor && error.constructor.name) || 'Error',
        message: (error && error.message) || String(error),
        stack_trace: (error && error.stack) || '',
        service_name: this.serviceName,
        environment: this.environment,
        metadata: Object.assign({}, metadata),
      };
      this._queue.push(payload);
    } catch (_) {
      // never crash the host application
    }
  }

  /**
   * Returns an Express 4-argument error-handling middleware.
   * Place AFTER all routes: app.use(reporter.middleware())
   */
  middleware() {
    const reporter = this;
    return function incidentReporterMiddleware(err, req, res, next) {
      try {
        reporter.captureError(err, {
          path: req.path || req.url,
          method: req.method,
          user_id: (req.user && req.user.id != null) ? String(req.user.id) : undefined,
        });
      } catch (_) {}
      next(err);
    };
  }

  async _flush() {
    if (this._queue.length === 0) return;
    const batch = this._queue.splice(0);
    for (const payload of batch) {
      await this._sendWithRetry(payload);
    }
  }

  async _sendWithRetry(payload, attempt = 0) {
    try {
      await this._post(`${this.apiUrl}/api/errors`, payload);
    } catch (_err) {
      if (attempt < this.maxRetries) {
        await this._sleep(Math.pow(2, attempt) * 1000); // 1s, 2s, 4s …
        return this._sendWithRetry(payload, attempt + 1);
      }
      this._writeFallback(payload);
    }
  }

  _post(url, body) {
    return new Promise((resolve, reject) => {
      const data = JSON.stringify(body);
      const parsed = new URL(url);
      const isHttps = parsed.protocol === 'https:';
      const lib = isHttps ? https : http;

      const options = {
        hostname: parsed.hostname,
        port: parsed.port || (isHttps ? 443 : 80),
        path: parsed.pathname + (parsed.search || ''),
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(data),
          ...(this.apiKey ? { 'X-API-Key': this.apiKey } : {}),
        },
        timeout: 5000,
      };

      const req = lib.request(options, (res) => {
        let responseBody = '';
        res.on('data', (chunk) => { responseBody += chunk; });
        res.on('end', () => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            try { resolve(JSON.parse(responseBody)); } catch (_) { resolve(responseBody); }
          } else {
            reject(new Error(`HTTP ${res.statusCode}: ${responseBody}`));
          }
        });
      });

      req.on('error', reject);
      req.on('timeout', () => { req.destroy(new Error('Request timed out')); });
      req.write(data);
      req.end();
    });
  }

  _writeFallback(payload) {
    try {
      const entry = JSON.stringify({ timestamp: new Date().toISOString(), ...payload });
      fs.appendFileSync(this.fallbackLogPath, entry + '\n', 'utf8');
    } catch (_) {}
  }

  _sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /** Flush remaining queue and stop the auto-flush timer. */
  async shutdown() {
    clearInterval(this._timer);
    return this._flush();
  }
}

module.exports = { IncidentReporter };
