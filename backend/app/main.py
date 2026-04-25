import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import api_keys, errors, incidents, stats

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
    logger.info("Pre-loading embedding model...")
    from app.services.embedding_service import get_model
    get_model()

    logger.info("Syncing Prometheus gauges from DB...")
    from app.database import SessionLocal
    from app.services.metrics_service import sync_gauges_from_db
    db = SessionLocal()
    try:
        sync_gauges_from_db(db)
    finally:
        db.close()

    logger.info("Ready")
    yield
    logger.info("Shutting down")


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

app.include_router(errors.router)
app.include_router(incidents.router)
app.include_router(stats.router)
app.include_router(api_keys.router)


@app.get("/health", tags=["health"])
@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
