# AI Incident Response System

**Production-grade AI-powered error monitoring with automatic root cause diagnosis**

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-Upstash-DC382D?style=flat&logo=redis&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-llama--3.1--8b-F55036?style=flat)

**Live Demo:** https://ai-incident-response-eight.vercel.app  
**API:** https://ai-incident-response-production.up.railway.app

---

## What It Does

AI Incident Response System automatically captures errors from any Python or Node.js application, clusters similar errors into incidents using SHA256 fingerprinting, and uses Groq LLM (llama-3.1-8b-instant) to diagnose root causes with specific code fixes — all within 2 seconds.

One line of code in your app. Automatic grouping, diagnosis, and alerting from there.

---

## Key Metrics

| Metric | Value |
|--------|-------|
| AI diagnosis response time | **< 2 seconds** (Groq llama-3.1-8b-instant) |
| Unit tests | **36** (22 pytest + 14 Jest) |
| SDKs | **2** — Python + Node.js |
| Supported frameworks | **5** — FastAPI, Flask, Django, Express, raw HTTP |
| Retry strategy | **3 attempts** with exponential backoff (1s → 2s → 4s) |
| Batch ingestion | **Up to 100 errors per request** |
| Uptime | **100%** on Railway + Vercel free tier |

---

## Architecture

```
Client Apps (FastAPI / Flask / Django / Express)
        ↓  SDK (1-line integration)
  FastAPI Backend (Railway)
        ↓              ↓            ↓
  PostgreSQL        Redis        Groq API
  (Supabase)      (Upstash)    (llama-3.1)
        ↓
  React Dashboard (Vercel)
```

---

## Features

- **SHA256 fingerprint-based deduplication** — identical errors cluster into one incident, not thousands of rows
- **LLM root cause diagnosis** — Groq API generates a root cause explanation and copy-paste code fix per incident
- **Auto-reactivation** — when a resolved incident recurs, it reactivates with a fresh timestamp and diagnosis cycle
- **Python SDK** — FastAPI middleware, Flask WSGI middleware, Django middleware
- **Node.js SDK** — Express error middleware
- **API key auth** — per-organization key management
- **MTTR tracking** — time-to-resolve recorded on every incident closure
- **Prometheus `/metrics` endpoint** — plug into any existing monitoring stack
- **Feedback loop** — thumbs up/down on each AI diagnosis to track accuracy

---

## Integration

**Python — 3 lines**

```python
from incident_reporter import IncidentReporter

reporter = IncidentReporter(api_url="https://ai-incident-response-production.up.railway.app", service_name="my-service", api_key="your-key")
reporter.setup_fastapi(app)   # or .register_flask_app(app) / DjangoMiddleware
```

**Node.js — 3 lines**

```javascript
const { IncidentReporter } = require('incident-reporter')

const reporter = new IncidentReporter({ apiUrl: 'https://ai-incident-response-production.up.railway.app', serviceName: 'my-service', apiKey: 'your-key' })
app.use(reporter.middleware())
```

Errors are captured automatically from that point. No try/catch changes needed.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.11, SQLAlchemy 2.0 |
| Database | PostgreSQL 16 (Supabase) |
| Cache | Redis (Upstash) |
| AI | Groq API, llama-3.1-8b-instant |
| Frontend | React 18, Vite, Tailwind CSS |
| Deployment | Railway (backend), Vercel (frontend) |
| Testing | pytest — 22 tests, Jest — 14 tests |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/errors` | Ingest a single error |
| `POST` | `/api/errors/batch` | Batch ingest up to 100 errors |
| `GET` | `/api/incidents` | List incidents (paginated, filterable by status/service/severity) |
| `GET` | `/api/incidents/{id}` | Get incident detail with full error list |
| `GET` | `/api/incidents/{id}/diagnose` | Trigger or fetch AI root cause diagnosis |
| `POST` | `/api/incidents/{id}/resolve` | Mark incident resolved, record MTTR |
| `POST` | `/api/incidents/{id}/feedback` | Submit thumbs up/down on AI diagnosis |
| `GET` | `/api/stats` | System-wide stats (incidents, errors, MTTR) |
| `POST` | `/api/api-keys` | Create an API key for an organization |
| `GET` | `/api/api-keys` | List API keys |
| `DELETE` | `/api/api-keys/{id}` | Revoke an API key |
| `GET` | `/metrics` | Prometheus metrics |

---

## Local Setup

**With Docker (recommended)**

```bash
docker compose up -d
```

**Without Docker**

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Required environment variables:

```env
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
GROQ_API_KEY=gsk_...
SECRET_KEY=...
```

---

## SDK Features

| Feature | Python | Node.js |
|---------|--------|---------|
| Auto-flush every 5s | ✓ | ✓ |
| Retry with backoff (1s, 2s, 4s) | ✓ | ✓ |
| Local fallback log when API unreachable | ✓ | ✓ |
| < 5ms overhead per request | ✓ | ✓ |
| Never crashes host application | ✓ | ✓ |
| Batch ingest (up to 100 errors) | ✓ | — |

---

<!--
RESUME BULLETS (copy to resume):

AI Incident Response System | FastAPI, PostgreSQL, Groq API, React
- Production SaaS capturing errors from Python/Node.js apps with
  1-line SDK integration (FastAPI, Flask, Django, Express middleware)
- LLM-powered root cause diagnosis via Groq API (llama-3.1-8b-instant)
  with <2s response time and automatic code fix suggestions
- SHA256 fingerprint-based error clustering with auto-reactivation
  of resolved incidents on recurrence
- 36 unit tests (22 pytest + 14 Jest), batch ingestion API (100 errors/req),
  exponential backoff retry (1s/2s/4s), Prometheus metrics endpoint
- Live: https://ai-incident-response-eight.vercel.app
-->
