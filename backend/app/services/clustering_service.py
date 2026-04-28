from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError
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


def cluster_error(db: Session, error: Error, user_id: Optional[int] = None) -> tuple[Incident, bool]:
    """
    Assign error to an existing incident with matching fingerprint and user_id,
    or create a new one. Returns (incident, is_new_incident).

    Resolved incidents are reactivated (returns True so diagnosis reruns).
    Active incidents are updated in-place (returns False).
    """
    fingerprint = _fingerprint_from_error(error)

    existing = (
        db.query(Incident)
        .filter(Incident.fingerprint == fingerprint, Incident.user_id == user_id)
        .first()
    )

    if existing:
        now = datetime.utcnow()
        if existing.status == IncidentStatus.resolved:
            existing.status = IncidentStatus.active
            existing.first_seen = now
            existing.last_seen = now
            existing.occurrence_count += 1
            existing.resolved_at = None
            existing.resolution_notes = None
            existing.mttr_seconds = None
            existing.ai_diagnosis = None
            existing.diagnosis_version = 0
            existing.last_diagnosed_at = None
            db.commit()
            db.refresh(existing)
            return existing, True

        existing.occurrence_count += 1
        existing.last_seen = now
        db.commit()
        db.refresh(existing)
        return existing, False

    incident = Incident(
        fingerprint=fingerprint,
        user_id=user_id,
        service_name=error.service_name,
        error_type=error.error_type,
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
        occurrence_count=1,
    )

    try:
        with db.begin_nested():
            db.add(incident)
            db.flush()
        db.commit()
        db.refresh(incident)
        return incident, True
    except IntegrityError:
        # Race condition: another worker inserted the same fingerprint+user_id.
        existing = (
            db.query(Incident)
            .filter(Incident.fingerprint == fingerprint, Incident.user_id == user_id)
            .first()
        )
        existing.occurrence_count += 1
        existing.last_seen = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing, False
