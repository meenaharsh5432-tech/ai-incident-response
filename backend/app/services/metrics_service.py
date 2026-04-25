import logging

from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

incidents_total = Counter(
    "incidents_total",
    "Total incidents created since last restart",
    ["service", "severity"],
)

errors_ingested_total = Counter(
    "errors_ingested_total",
    "Total errors ingested since last restart",
    ["service", "environment"],
)

active_incidents_gauge = Gauge(
    "active_incidents_count",
    "Currently active incidents (synced from DB on startup)",
    ["service"],
)

# Persistent totals — gauges synced from DB, survive restarts correctly in Grafana
incidents_total_gauge = Gauge(
    "incidents_total_db",
    "Total incidents ever created (queried from DB)",
    [],
)

active_incidents_total_gauge = Gauge(
    "active_incidents_total_db",
    "Total currently active incidents (queried from DB)",
    [],
)

active_incidents_by_severity_gauge = Gauge(
    "active_incidents_by_severity_db",
    "Active incidents broken down by severity (queried from DB)",
    ["severity"],
)

mttr_histogram = Histogram(
    "mttr_seconds",
    "Time to resolve incidents",
    ["service"],
    buckets=[60, 300, 900, 3600, 14400, 86400, float("inf")],
)

ai_feedback_counter = Counter(
    "ai_diagnosis_feedback_total",
    "AI diagnosis feedback events",
    ["helpful", "service"],
)

cluster_size_histogram = Histogram(
    "error_cluster_size",
    "Errors per incident at resolution time",
    ["service"],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500],
)


def record_new_incident(service: str, severity: str) -> None:
    incidents_total.labels(service=service, severity=severity).inc()
    active_incidents_gauge.labels(service=service).inc()
    active_incidents_total_gauge.inc()
    incidents_total_gauge.inc()
    active_incidents_by_severity_gauge.labels(severity=severity).inc()


def record_error_ingested(service: str, environment: str) -> None:
    errors_ingested_total.labels(service=service, environment=environment).inc()


def record_resolution(service: str, severity: str, mttr_sec: float, cluster_size: int) -> None:
    active_incidents_gauge.labels(service=service).dec()
    active_incidents_total_gauge.dec()
    active_incidents_by_severity_gauge.labels(severity=severity).dec()
    mttr_histogram.labels(service=service).observe(mttr_sec)
    cluster_size_histogram.labels(service=service).observe(cluster_size)


def record_feedback(service: str, was_helpful: bool) -> None:
    ai_feedback_counter.labels(helpful=str(was_helpful).lower(), service=service).inc()


def sync_gauges_from_db(db) -> None:
    """Sync in-memory Prometheus gauges from the database.

    Must be called at startup (and optionally periodically) because
    gauge state is lost on every backend restart, which causes active_incidents_count
    to drift negative when incidents are resolved across restarts.
    """
    from sqlalchemy import func
    from app.models.incident import Incident, IncidentStatus

    try:
        # Per-service active incident counts
        rows = (
            db.query(Incident.service_name, func.count(Incident.id))
            .filter(Incident.status == IncidentStatus.active)
            .group_by(Incident.service_name)
            .all()
        )
        total_active = 0
        for service_name, count in rows:
            active_incidents_gauge.labels(service=service_name).set(count)
            total_active += count

        # Aggregate totals for the persistent gauges used in Grafana
        active_incidents_total_gauge.set(total_active)

        all_time_total = db.query(func.count(Incident.id)).scalar() or 0
        incidents_total_gauge.set(all_time_total)

        # Per-severity active breakdown
        severity_rows = (
            db.query(Incident.severity, func.count(Incident.id))
            .filter(Incident.status == IncidentStatus.active)
            .group_by(Incident.severity)
            .all()
        )
        for severity, count in severity_rows:
            sev = severity.value if hasattr(severity, "value") else str(severity)
            active_incidents_by_severity_gauge.labels(severity=sev).set(count)

        logger.info(
            "Synced Prometheus gauges from DB: active=%d, all_time=%d",
            total_active,
            all_time_total,
        )
    except Exception as exc:
        logger.error("Failed to sync Prometheus gauges from DB: %s", exc)
