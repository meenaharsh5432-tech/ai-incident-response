import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter

from app.config import get_settings
from app.database import init_db
from app.routers import api_keys, auth, errors, incidents, stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initialising database...")
    init_db()
    logger.info("Syncing Prometheus gauges from DB...")
    from app.database import SessionLocal
    from app.services.metrics_service import sync_gauges_from_db
    db = SessionLocal()
    try:
        sync_gauges_from_db(db)
    finally:
        db.close()

    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        await FastAPILimiter.init(redis_client)
        logger.info("Rate limiter initialized")
    except Exception as exc:
        logger.warning("Rate limiter disabled — Redis unavailable: %s", exc)

    logger.info(
        "Google OAuth configured: %s | JWT secret set: %s | Frontend URL: %s",
        bool(settings.OAUTH_GOOGLE_CLIENT_ID),
        bool(settings.JWT_SECRET and settings.JWT_SECRET != "change-me-in-production"),
        settings.FRONTEND_URL,
    )
    logger.info("Ready")
    yield
    logger.info("Shutting down")
    if FastAPILimiter.redis is not None:
        await FastAPILimiter.close()


app = FastAPI(
    title="AI Incident Response System",
    description="Semantic error clustering, AI diagnosis, and resolution tracking.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(errors.router)
app.include_router(incidents.router)
app.include_router(stats.router)
app.include_router(api_keys.router)


@app.get("/health", tags=["health"])
@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
