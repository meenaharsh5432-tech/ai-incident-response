from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models.error import Error
from app.models.feedback import Feedback
from app.models.incident import Incident, IncidentStatus
from app.models.user import User

router = APIRouter(tags=["observability"])


@router.get("/api/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    uid = current_user.id
    now = datetime.utcnow()
    day_ago = now - timedelta(hours=24)
    hour_ago = now - timedelta(hours=1)

    active_count = (
        db.query(func.count(Incident.id))
        .filter(Incident.user_id == uid, Incident.status == IncidentStatus.active)
        .scalar()
        or 0
    )

    critical_count = (
        db.query(func.count(Incident.id))
        .filter(
            Incident.user_id == uid,
            Incident.status == IncidentStatus.active,
            Incident.severity == "critical",
        )
        .scalar()
        or 0
    )

    resolved_24h = (
        db.query(func.count(Incident.id))
        .filter(
            Incident.user_id == uid,
            Incident.status == IncidentStatus.resolved,
            Incident.resolved_at >= day_ago,
        )
        .scalar()
        or 0
    )

    avg_mttr = (
        db.query(func.avg(Incident.mttr_seconds))
        .filter(Incident.user_id == uid, Incident.mttr_seconds.isnot(None))
        .scalar()
    )

    errors_last_hour = (
        db.query(func.count(Error.id))
        .filter(Error.user_id == uid, Error.created_at >= hour_ago)
        .scalar()
        or 0
    )

    helpful = (
        db.query(func.count(Feedback.id))
        .join(Incident, Feedback.incident_id == Incident.id)
        .filter(Incident.user_id == uid, Feedback.was_helpful.is_(True))
        .scalar()
        or 0
    )
    total_feedback = (
        db.query(func.count(Feedback.id))
        .join(Incident, Feedback.incident_id == Incident.id)
        .filter(Incident.user_id == uid)
        .scalar()
        or 0
    )

    errors_by_service = (
        db.query(
            Error.service_name,
            func.count(Error.id).label("count"),
        )
        .filter(Error.user_id == uid, Error.created_at >= day_ago)
        .group_by(Error.service_name)
        .all()
    )
    errors_by_service = sorted(errors_by_service, key=lambda row: row[1], reverse=True)

    mttr_by_service = (
        db.query(
            Incident.service_name,
            func.avg(Incident.mttr_seconds).label("avg_mttr"),
        )
        .filter(Incident.user_id == uid, Incident.mttr_seconds.isnot(None))
        .group_by(Incident.service_name)
        .all()
    )
    mttr_by_service = sorted(mttr_by_service, key=lambda row: row[1] or 0, reverse=True)

    timeline = []
    for hour in range(23, -1, -1):
        bucket_start = now - timedelta(hours=hour + 1)
        bucket_end = now - timedelta(hours=hour)
        count = (
            db.query(func.count(Error.id))
            .filter(
                Error.user_id == uid,
                Error.created_at >= bucket_start,
                Error.created_at < bucket_end,
            )
            .scalar()
            or 0
        )
        timeline.append({"hour": bucket_end.strftime("%H:%M"), "count": count})

    recent = (
        db.query(Incident)
        .filter(Incident.user_id == uid, Incident.status == IncidentStatus.active)
        .order_by(Incident.last_seen.desc())
        .limit(5)
        .all()
    )

    return {
        "last_updated": now.isoformat(),
        "active_incidents": active_count,
        "critical_incidents": critical_count,
        "resolved_last_24h": resolved_24h,
        "avg_mttr_seconds": round(avg_mttr, 1) if avg_mttr else None,
        "errors_last_hour": errors_last_hour,
        "ai_accuracy_rate": round(helpful / total_feedback * 100, 1) if total_feedback > 0 else None,
        "errors_by_service": [{"service": service, "count": count} for service, count in errors_by_service],
        "mttr_by_service": [
            {"service": service, "avg_mttr": round(avg_mttr_value, 1) if avg_mttr_value else 0}
            for service, avg_mttr_value in mttr_by_service
        ],
        "error_timeline": timeline,
        "recent_incidents": [
            {
                "id": incident.id,
                "service_name": incident.service_name,
                "error_type": incident.error_type,
                "severity": incident.severity,
                "occurrence_count": incident.occurrence_count,
                "last_seen": incident.last_seen.isoformat(),
            }
            for incident in recent
        ],
    }


@router.get("/metrics")
def prometheus_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
