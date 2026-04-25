from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.error import Error
from app.models.incident import Incident, IncidentStatus
from app.services.embedding_service import generate_fingerprint


def _fingerprint_from_error(error: Error) -> str:
    return generate_fingerprint(
        error.error_type or "",
        error.message or "",
        error.stack_trace,
    )


def find_similar_incident(db: Session, fingerprint: str) -> Optional[Incident]:
    return (
        db.query(Incident)
        .filter(Incident.fingerprint == fingerprint, Incident.status == IncidentStatus.active)
        .first()
    )


def cluster_error(db: Session, error: Error) -> tuple[Incident, bool]:
    """
    Assign error to an existing active incident with matching fingerprint,
    or create a new one. Returns (incident, is_new_incident).
    """
    fingerprint = _fingerprint_from_error(error)
    existing = find_similar_incident(db, fingerprint)

    if existing:
        existing.occurrence_count += 1
        existing.last_seen = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing, False

    incident = Incident(
        fingerprint=fingerprint,
        service_name=error.service_name,
        error_type=error.error_type,
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
        occurrence_count=1,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident, True
