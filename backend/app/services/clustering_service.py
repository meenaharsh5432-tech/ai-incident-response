import hashlib
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.error import Error
from app.models.incident import Incident, IncidentStatus

settings = get_settings()


def _generate_fingerprint() -> str:
    return hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:32]


def _format_vector(embedding: list[float]) -> str:
    """Format embedding list as pgvector literal."""
    return "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"


def find_similar_incident(db: Session, embedding: list[float]) -> Optional[Incident]:
    """
    Use pgvector cosine distance to find the nearest active incident.
    Cosine distance = 1 - cosine_similarity, so threshold 0.85 sim → 0.15 dist.
    """
    vec_str = _format_vector(embedding)
    threshold = 1.0 - settings.SIMILARITY_THRESHOLD

    row = db.execute(
        text("""
            SELECT id, (representative_embedding <=> CAST(:emb AS vector)) AS dist
            FROM incidents
            WHERE status = 'active'
              AND representative_embedding IS NOT NULL
            ORDER BY representative_embedding <=> CAST(:emb AS vector)
            LIMIT 1
        """),
        {"emb": vec_str},
    ).fetchone()

    if row and row[1] <= threshold:
        return db.get(Incident, row[0])

    return None


def cluster_error(db: Session, error: Error) -> tuple[Incident, bool]:
    """
    Assign error to an existing incident (semantic match) or create a new one.
    Returns (incident, is_new_incident).
    """
    existing = find_similar_incident(db, error.embedding)

    if existing:
        existing.occurrence_count += 1
        existing.last_seen = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing, False

    incident = Incident(
        fingerprint=_generate_fingerprint(),
        service_name=error.service_name,
        error_type=error.error_type,
        representative_embedding=error.embedding,
        first_seen=datetime.utcnow(),
        last_seen=datetime.utcnow(),
        occurrence_count=1,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident, True
