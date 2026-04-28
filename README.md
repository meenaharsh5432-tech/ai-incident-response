# AI Incident Response System

**Incidents don't wait. Neither should your team. Detect, diagnose, and resolve in one place.**

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat&logo=redis&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-llama--3.1--8b-F55036?style=flat)

**Live Demo:** https://ai-incident-response-eight.vercel.app  
**API:** https://ai-incident-response-production.up.railway.app

---

## What It Does

AI Incident Response automatically captures errors from any Python or Node.js application, clusters similar errors into incidents using SHA256 fingerprinting, and uses Groq LLM to diagnose root causes with specific code fixes — all within 2 seconds.

Each user gets their own isolated incident workspace via Google OAuth. One line of code in your app. Automatic grouping, diagnosis, and resolution tracking from there.

---

## Key Features

- **Google OAuth** — per-user incident isolation, no shared data between accounts
- **SHA256 fingerprint clustering** — identical errors group into one incident, not thousands of rows
- **LLM root cause diagnosis** — Groq API generates a root cause + copy-paste code fix per incident
- **Auto-reactivation** — resolved incidents reactivate automatically when the same error recurs
- **Python & Node.js SDKs** — FastAPI, Flask, Django, Express middleware with 1-line setup
- **Per-user API keys** — scoped to your account, errors are attributed to the key owner
- **MTTR tracking** — time-to-resolve recorded on every incident closure
- **Prometheus `/metrics`** — plug into any existing monitoring stack
- **AI feedback loop** — thumbs up/down on diagnoses to track accuracy over time
- **Rate limiting** — Redis-backed per-IP limits on all endpoints
- **IST timezone** — error timeline displayed in Indian Standard Time

---

## Architecture

```
Client Apps (FastAPI / Flask / Django / Express)
        ↓  SDK (1-line integration) + X-API-Key
  FastAPI Backend (Railway)
        ↓              ↓            ↓
  PostgreSQL        Redis        Groq API
  (per-user)      (rate limit) (llama-3.1)
        ↓
  React Dashboard (Vercel) — Google OAuth
```

---

## Key Metrics

| Metric | Value |
|--------|-------|
| AI diagnosis latency | **< 2s** (Groq llama-3.1-8b-instant) |
| SDKs | **2** — Python + Node.js |
| Supported frameworks | **5** — FastAPI, Flask, Django, Express, raw HTTP |
| Batch ingestion | **Up to 100 errors/request** |
| Rate limits | **100 req/min** (errors), **10 req/min** (diagnose) |
| Unit tests | **36** (22 pytest + 14 Jest) |

---

## Integration

**Python — 3 lines**

```python
from incident_reporter import IncidentReporter

reporter = IncidentReporter(
    api_url="https://ai-incident-response-production.up.railway.app",
    service_name="my-service",
    api_key="your-key"   # create in dashboard → API Keys tab
)
reporter.setup_fastapi(app)   # or .register_flask_app(app) / DjangoMiddleware
```

**Node.js — 3 lines**

```javascript
const { IncidentReporter } = require('incident-reporter')

const reporter = new IncidentReporter({
    apiUrl: 'https://ai-incident-response-production.up.railway.app',
    serviceName: 'my-service',
    apiKey: 'your-key'
})
app.use(reporter.middleware())
```

Errors are captured automatically. No try/catch changes needed.

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/errors` | API key | Ingest a single error |
| `POST` | `/api/errors/batch` | API key | Batch ingest up to 100 errors |
| `GET` | `/api/incidents` | JWT | List incidents (paginated, filterable) |
| `GET` | `/api/incidents/{id}` | JWT | Incident detail with full error list |
| `GET` | `/api/incidents/{id}/diagnose` | JWT | Trigger AI root cause diagnosis |
| `POST` | `/api/incidents/{id}/resolve` | JWT | Mark resolved, record MTTR |
| `POST` | `/api/incidents/{id}/feedback` | JWT | Thumbs up/down on AI diagnosis |
| `GET` | `/api/stats` | JWT | Per-user stats (incidents, errors, MTTR) |
| `POST` | `/api/keys` | JWT | Create an API key |
| `GET` | `/api/keys` | JWT | List your API keys |
| `DELETE` | `/api/keys/{id}` | JWT | Revoke an API key |
| `GET` | `/auth/google` | — | Start Google OAuth flow |
| `GET` | `/auth/me` | JWT | Get current user info |
| `GET` | `/metrics` | — | Prometheus metrics |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI 0.115, Python 3.11, SQLAlchemy 2.0 |
| Database | PostgreSQL 16 with pgvector |
| Cache / Rate limiting | Redis 7 |
| AI | Groq API, llama-3.1-8b-instant |
| Auth | Google OAuth 2.0, JWT (python-jose) |
| Frontend | React 18, Vite, Tailwind CSS |
| Deployment | Railway (backend), Vercel (frontend) |
| Testing | pytest (22 tests), Jest (14 tests) |

---

## Local Setup

**With Docker**

```bash
docker compose up -d
```

**Without Docker**

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

**Required env vars (`backend/.env`)**

```env
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
GROQ_API_KEY=gsk_...
OAUTH_GOOGLE_CLIENT_ID=...
OAUTH_GOOGLE_CLIENT_SECRET=...
OAUTH_GOOGLE_REDIRECT_URI=http://localhost:8001/auth/google/callback
JWT_SECRET=...
FRONTEND_URL=http://localhost:5173
```

**Seed test data**

```bash
# 1. Create an API key in the dashboard → API Keys tab
# 2. Run the seed script
python seed_errors.py  --url https://ai-incident-response-production.up.railway.app  --api-key <your-key>
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
RESUME BULLETS 

AI Incident Response System | FastAPI, PostgreSQL, Groq API, React, Google OAuth
- Production SaaS with Google OAuth for per-user incident isolation; errors attributed
  to API key owners with full multi-tenant data scoping across all endpoints
- LLM-powered root cause diagnosis via Groq API (llama-3.1-8b-instant) with <2s
  response time, auto-reactivation on recurrence, and AI feedback tracking
- SHA256 fingerprint clustering with Redis-backed rate limiting (fastapi-limiter),
  JWT auth (python-jose), and idempotent schema migrations on startup
- 1-line SDK integration for FastAPI, Flask, Django, Express; 36 unit tests,
  batch ingestion (100 errors/req), Prometheus metrics endpoint
- Live: https://ai-incident-response-eight.vercel.app
-->
