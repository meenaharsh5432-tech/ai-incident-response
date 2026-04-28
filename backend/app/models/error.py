from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Error(Base):
    __tablename__ = "errors"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    message = Column(Text)
    stack_trace = Column(Text, nullable=True)
    error_type = Column(String(200))
    service_name = Column(String(100), index=True)
    environment = Column(String(50), default="prod")
    metadata_ = Column("metadata", JSON, nullable=True)
    embedding = Column(Vector(384), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    incident = relationship("Incident", back_populates="errors")
