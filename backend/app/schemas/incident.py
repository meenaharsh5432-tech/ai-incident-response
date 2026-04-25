from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

from app.schemas.error import ErrorDetail


class IncidentSummary(BaseModel):
    id: int
    fingerprint: str
    service_name: str
    error_type: str
    first_seen: datetime
    last_seen: datetime
    occurrence_count: int
    status: str
    severity: str
    ai_diagnosis: Optional[dict[str, Any]] = None
    resolved_at: Optional[datetime] = None
    mttr_seconds: Optional[float] = None

    model_config = {"from_attributes": True}


class IncidentDetail(IncidentSummary):
    errors: list[ErrorDetail] = []
    resolution_notes: Optional[str] = None
    last_diagnosed_at: Optional[datetime] = None


class ResolveRequest(BaseModel):
    resolution_notes: Optional[str] = None


class PaginatedIncidents(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[IncidentSummary]
