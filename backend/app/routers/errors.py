import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from app.limiter import OptionalRateLimiter
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.api_key import APIKey
from app.models.error import Error
from app.schemas.error import (
    BatchErrorResponse,
    ErrorBatchIngest,
    ErrorIngest,
    ErrorResponse,
)
from app.services import clustering_service, metrics_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/errors", tags=["errors"])


def _get_api_key(
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[APIKey]:
    settings = get_settings()
    if not settings.REQUIRE_API_KEY:
        return None  # auth disabled — allow all requests

    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    api_key = (
        db.query(APIKey)
        .filter(APIKey.key == x_api_key, APIKey.is_active == True)  # noqa: E712
        .first()
    )
    if not api_key:
        raise HTTPException(status_code=403, detail="Invalid or revoked API key")
    return api_key


def _ingest_one(
    payload: ErrorIngest,
    db: Session,
) -> ErrorResponse:
    error = Error(
        message=payload.message,
        stack_trace=payload.stack_trace,
        error_type=payload.error_type,
        service_name=payload.service_name,
        environment=payload.environment.value,
        metadata_=payload.metadata,
        embedding=None,
    )
    db.add(error)
    db.flush()

    incident, is_new = clustering_service.cluster_error(db, error)
    error.incident_id = incident.id
    db.commit()
    db.refresh(error)

    metrics_service.record_error_ingested(payload.service_name, payload.environment.value)
    if is_new:
        metrics_service.record_new_incident(payload.service_name, incident.severity.value)

    return ErrorResponse(
        id=error.id,
        incident_id=incident.id,
        error_type=error.error_type,
        service_name=error.service_name,
        environment=error.environment,
        created_at=error.created_at,
        is_new_incident=is_new,
    )


@router.post("", response_model=ErrorResponse, status_code=201, dependencies=[Depends(OptionalRateLimiter(times=100, seconds=60))])
def ingest_error(
    payload: ErrorIngest,
    db: Session = Depends(get_db),
    _api_key: Optional[APIKey] = Depends(_get_api_key),
):
    return _ingest_one(payload, db)


@router.post("/batch", response_model=BatchErrorResponse, status_code=201, dependencies=[Depends(OptionalRateLimiter(times=20, seconds=60))])
def ingest_errors_batch(
    payload: ErrorBatchIngest,
    db: Session = Depends(get_db),
    _api_key: Optional[APIKey] = Depends(_get_api_key),
):
    """Ingest multiple errors at once. Duplicate error_type+message pairs within
    the same batch are deduplicated before processing."""
    seen: set = set()
    unique_errors = []
    deduplicated = 0

    for err in payload.errors:
        dedup_key = (err.error_type, err.message)
        if dedup_key in seen:
            deduplicated += 1
            continue
        seen.add(dedup_key)
        unique_errors.append(err)

    results = []
    for err in unique_errors:
        results.append(_ingest_one(err, db))

    return BatchErrorResponse(
        processed=len(unique_errors),
        deduplicated=deduplicated,
        results=results,
    )
