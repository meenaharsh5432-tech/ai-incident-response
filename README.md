# AI Incident Response System

Production-grade backend service that automatically captures, semantically clusters, AI-diagnoses, and tracks resolution of application errors.

## Architecture

```
Errors → FastAPI → sentence-transformers (embed) → pgvector (cluster)
                 ↓
            Groq LLaMA-3.1 (diagnose) → PostgreSQL
                 ↓
          Prometheus metrics → Grafana dashboards
                 ↓
          React dashboard (port 3000)
```

## Quick Start

### 1. Configure

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY (free at console.groq.com)
```

### 2. Launch all services

```bash
docker-compose up --build
```

First run downloads the `all-MiniLM-L6-v2` model (~80 MB) during the backend image build.

### 3. Seed test data

```bash
python seed_errors.py --repeat 3
```

### 4. Open the dashboard

| Service    | URL                        |
|------------|----------------------------|
| Dashboard  | http://localhost:3000       |
| API docs   | http://localhost:8000/docs  |
| Prometheus | http://localhost:9090       |
| Grafana    | http://localhost:3001 (admin/admin) |

## API Reference

```
POST /api/errors                     Ingest a single error
POST /api/errors/batch               Ingest up to 100 errors at once (deduplicates within batch)
GET  /api/incidents                  List incidents (filter: status, service, severity)
GET  /api/incidents/:id              Incident detail + all errors + diagnosis
POST /api/incidents/:id/resolve      Mark resolved (optionally add notes)
POST /api/incidents/:id/feedback     Rate AI diagnosis helpfulness
GET  /api/stats                      Dashboard stats
GET  /metrics                        Prometheus metrics
POST /api/keys                       Generate API key for a service
GET  /api/keys                       List active API keys
DELETE /api/keys/:id                 Revoke an API key
```

### Ingest an error (example)

```bash
curl -X POST http://localhost:8000/api/errors \
  -H "Content-Type: application/json" \
  -d '{
    "error_type": "DatabaseConnectionError",
    "message": "connection pool exhausted",
    "stack_trace": "File app/db.py line 42 ...",
    "service_name": "user-service",
    "environment": "prod",
    "metadata": {"cpu": 92, "memory_mb": 1800}
  }'
```

## How clustering works

1. Each error message + stack trace is embedded with `all-MiniLM-L6-v2` (384-dim)
2. pgvector cosine distance query finds the nearest active incident
3. Distance < 0.15 (= similarity > 0.85) → grouped into existing incident
4. Otherwise → new incident created, AI diagnosis triggered as a background task

## Prometheus metrics exposed

| Metric | Labels |
|--------|--------|
| `incidents_total` | service, severity |
| `errors_ingested_total` | service, environment |
| `active_incidents_count` | service |
| `mttr_seconds` (histogram) | service |
| `ai_diagnosis_feedback_total` | helpful, service |
| `error_cluster_size` (histogram) | service |

## Integrate in 2 minutes

### Python (FastAPI / Flask / Django)

```bash
pip install -e .           # from repo root
```

**FastAPI**
```python
from incident_reporter import IncidentReporter

reporter = IncidentReporter(
    api_url="http://your-backend:8000",
    service_name="my-service",
    api_key="your-api-key",           # optional
)
reporter.setup_fastapi(app)           # registers exception handler + ASGI middleware
```

**Flask**
```python
from incident_reporter import IncidentReporter

reporter = IncidentReporter(api_url="...", service_name="my-service")
reporter.register_flask_app(app)      # registers @app.errorhandler(Exception)

# Or WSGI wrapper:
from incident_reporter import flask_middleware
app.wsgi_app = flask_middleware(app.wsgi_app, reporter)
```

**Django** — add to `settings.py`:
```python
from incident_reporter.middleware import DjangoMiddleware
DjangoMiddleware.configure(reporter)  # call at app startup

MIDDLEWARE = [
    "incident_reporter.middleware.DjangoMiddleware",
    ...
]
```

**Decorator** (any framework):
```python
from incident_reporter import capture_errors

@capture_errors(reporter)
def process_order(order_id, payment_token):
    ...   # exceptions auto-captured, then re-raised
```

That's it. Every unhandled error appears in your dashboard with AI diagnosis.

---

### Node.js (Express)

```bash
npm install ./incident-reporter-node
```

```javascript
const { IncidentReporter } = require('incident-reporter');

const reporter = new IncidentReporter({
  apiUrl: 'http://your-backend:8000',
  serviceName: 'my-service',
  apiKey: 'your-api-key',             // optional
});

// Place AFTER all routes:
app.use(reporter.middleware());
```

---

### SDK features

| Feature | Python | Node.js |
|---------|--------|---------|
| Auto-flush every 5s | ✓ | ✓ |
| Retry with backoff (1s, 2s, 4s) | ✓ | ✓ |
| Local fallback log when API unreachable | `incident_fallback.log` | `incident_fallback.log` |
| <5ms overhead per request | ✓ | ✓ |
| Never crashes host application | ✓ | ✓ |
| Batch ingest (up to 100 errors) | `POST /api/errors/batch` | — |

---

### API Key management

```bash
# Create a key for a service
curl -X POST http://localhost:8000/api/keys \
  -H "Content-Type: application/json" \
  -d '{"service_name": "payment-service", "description": "prod key"}'

# List active keys
curl http://localhost:8000/api/keys

# Revoke a key
curl -X DELETE http://localhost:8000/api/keys/1
```

Enable enforcement in `.env`:
```
REQUIRE_API_KEY=true
```

---

### One-command demo

```bash
# Start all example apps and flood them with realistic traffic:
bash run_demo.sh
```

This starts FastAPI (:8001), Flask (:8002), Express (:8003), runs 60s of traffic
at 30% error rate, and prints a summary of errors generated across all services.

---

## Development (without Docker)

```bash
# Postgres + Redis via Docker
docker-compose up postgres redis -d

cd backend
pip install -r requirements.txt
cp ../.env.example .env   # set DATABASE_URL / REDIS_URL to localhost
uvicorn app.main:app --reload

cd ../frontend
npm install
npm run dev   # http://localhost:5173
```
