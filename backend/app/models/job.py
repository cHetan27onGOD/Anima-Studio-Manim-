import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class JobStatus(str, enum.Enum):
    """Job status enumeration."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Job(Base):
    """Job model representing a rendering task."""

    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt = Column(Text, nullable=False)
    status = Column(
        Enum(JobStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=JobStatus.QUEUED,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    plan_json = Column(JSONB, nullable=True)  # LLM-generated animation plan
    video_filename = Column(Text, nullable=True)
    code = Column(Text, nullable=True)
    logs = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    progress = Column(JSONB, nullable=True)  # Store progress as int or dict
    
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    owner = relationship("User", back_populates="jobs")

    def __repr__(self):
        return f"<Job {self.id} status={self.status}>"
