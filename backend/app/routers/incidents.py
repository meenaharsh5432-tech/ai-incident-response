from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.feedback import Feedback
from app.models.incident import Incident, IncidentStatus
from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.schemas.incident import IncidentDetail, IncidentSummary, PaginatedIncidents, ResolveRequest
from app.services import metrics_service

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("", response_model=PaginatedIncidents)
def list_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    service: str = Query(None),
    severity: str = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Incident).order_by(desc(Incident.last_seen))

    if status:
        q = q.filter(Incident.status == status)
    if service:
        q = q.filter(Incident.service_name == service)
    if severity:
        q = q.filter(Incident.severity == severity)

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedIncidents(total=total, page=page, page_size=page_size, items=items)


@router.get("/{incident_id}", response_model=IncidentDetail)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.post("/{incident_id}/resolve")
def resolve_incident(
    incident_id: int,
    body: ResolveRequest,
    db: Session = Depends(get_db),
):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    if incident.status == IncidentStatus.resolved:
        raise HTTPException(status_code=400, detail="Incident is already resolved")

    now = datetime.utcnow()
    incident.status = IncidentStatus.resolved
    incident.resolved_at = now
    incident.resolution_notes = body.resolution_notes
    incident.mttr_seconds = (now - incident.first_seen).total_seconds()
    db.commit()

    metrics_service.record_resolution(
        incident.service_name,
        incident.severity.value,
        incident.mttr_seconds,
        incident.occurrence_count,
    )

    return {"message": "Incident resolved", "mttr_seconds": incident.mttr_seconds}


@router.post("/{incident_id}/feedback", response_model=FeedbackResponse, status_code=201)
def add_feedback(
    incident_id: int,
    body: FeedbackCreate,
    db: Session = Depends(get_db),
):
    incident = db.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    feedback = Feedback(
        incident_id=incident_id,
        was_helpful=body.was_helpful,
        actual_fix=body.actual_fix,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    metrics_service.record_feedback(incident.service_name, body.was_helpful)
    return feedback
