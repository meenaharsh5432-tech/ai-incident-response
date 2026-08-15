import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.error import Error
from app.models.incident import Incident, IncidentStatus
from app.services.embedding_service import generate_fingerprint

logger = logging.getLogger(__name__)
settings = get_settings()


def _fingerprint_from_error(error: Error) -> str:
    return generate_fingerprint(
        error.error_type or "",
        error.message or "",
        error.stack_trace,
    )


def _find_similar_incident(
    db: Session, embedding: list[float], user_id: Optional[int]
) -> Optional[Incident]:
    """Nearest incident by cosine distance, if it clears SIMILARITY_THRESHOLD.

    Vectors are normalized at encode time, so cosine distance = 1 - similarity.
    """
    max_distance = 1.0 - settings.SIMILARITY_THRESHOLD

    try:
        distance = Incident.representative_embedding.cosine_distance(embedding)
        row = (
            db.query(Incident, distance.label("distance"))
            .filter(
                Incident.user_id == user_id,
                Incident.representative_embedding.isnot(None),
            )
            .order_by(distance)
            .limit(1)
            .first()
        )
    except Exception as exc:
        logger.warning("Similarity search failed, using fingerprint only: %s", exc)
        return None

    if row is None or row.distance > max_distance:
        return None

    logger.info(
        "Semantic match: incident %s at similarity %.3f",
        row.Incident.id, 1.0 - row.distance,
    )
    return row.Incident


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

    if existing is None and error.embedding is not None:
        # No exact fingerprint match — fall back to semantic similarity so the same
        # bug with differently-worded messages lands on one incident.
        existing = _find_similar_incident(db, error.embedding, user_id)

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
        representative_embedding=error.embedding,
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
        if existing is None:
            raise
        existing.occurrence_count += 1
        existing.last_seen = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing, False
