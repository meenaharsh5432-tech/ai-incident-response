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


def find_similar_incident(db: Session, fingerprint: str) -> Optional[Incident]:
    return (
        db.query(Incident)
        .filter(Incident.fingerprint == fingerprint, Incident.status == IncidentStatus.active)
        .first()
    )


def cluster_error(db: Session, error: Error) -> tuple[Incident, bool]:
    """
    Assign error to an existing incident with matching fingerprint, or create
    a new one. Returns (incident, is_new_incident).

    Resolved incidents are reactivated (returns True so diagnosis reruns).
    Active incidents are updated in-place (returns False).
    """
    fingerprint = _fingerprint_from_error(error)

    # Step 1: look for any existing incident with this fingerprint (any status).
    existing = (
        db.query(Incident)
        .filter(Incident.fingerprint == fingerprint)
        .first()
    )

    if existing:
        now = datetime.utcnow()
        if existing.status == IncidentStatus.resolved:
            # Reactivate: reset timestamps and wipe all resolution data so the
            # incident starts fresh for a new resolution cycle.
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

        # Step 2: active (or suppressed) — bump counters and return.
        existing.occurrence_count += 1
        existing.last_seen = now
        db.commit()
        db.refresh(existing)
        return existing, False

    # Step 3: not found — create a new incident.
    incident = Incident(
        fingerprint=fingerprint,
        service_name=error.service_name,
        error_type=error.error_type,
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
        occurrence_count=1,
    )

    try:
        # Use a savepoint so a concurrent UniqueViolation only rolls back this
        # INSERT — the outer transaction (including the caller's error flush) stays
        # intact. A plain db.rollback() would undo the error flush and crash the
        # caller when it later calls db.refresh(error).
        with db.begin_nested():
            db.add(incident)
            db.flush()
        db.commit()
        db.refresh(incident)
        return incident, True
    except IntegrityError:
        # Race condition: another worker inserted the same fingerprint between
        # our SELECT and INSERT. The savepoint was rolled back; fetch that winner.
        existing = (
            db.query(Incident)
            .filter(Incident.fingerprint == fingerprint)
            .first()
        )
        existing.occurrence_count += 1
        existing.last_seen = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing, False
