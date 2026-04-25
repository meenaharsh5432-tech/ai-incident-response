import enum
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Enum as SAEnum, Float, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class IncidentStatus(str, enum.Enum):
    active = "active"
    resolved = "resolved"
    suppressed = "suppressed"


class IncidentSeverity(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    fingerprint = Column(String(64), unique=True, index=True)
    service_name = Column(String(100), index=True)
    error_type = Column(String(200), index=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    occurrence_count = Column(Integer, default=1)
    status = Column(SAEnum(IncidentStatus), default=IncidentStatus.active, index=True)
    severity = Column(SAEnum(IncidentSeverity), default=IncidentSeverity.medium, index=True)
    ai_diagnosis = Column(JSON, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    mttr_seconds = Column(Float, nullable=True)
    # 384-dim vector from all-MiniLM-L6-v2
    representative_embedding = Column(Vector(384), nullable=True)
    diagnosis_version = Column(Integer, default=0)
    last_diagnosed_at = Column(DateTime, nullable=True)

    errors = relationship("Error", back_populates="incident", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="incident", cascade="all, delete-orphan")
