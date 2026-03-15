from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.job import JobStatus


class JobCreate(BaseModel):
    """Schema for creating a new job."""

    prompt: str = Field(..., min_length=1, max_length=1000, description="Graph description prompt")


class JobResponse(BaseModel):
    """Schema for job response."""

    id: UUID
    prompt: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    plan_json: Optional[dict[str, Any]] = None
    video_filename: Optional[str] = None
    code: Optional[str] = None
    logs: Optional[str] = None
    error: Optional[str] = None
    progress: Optional[Any] = None
    owner_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class JobUpdate(BaseModel):
    """Schema for updating a job."""

    code: Optional[str] = None


class JobRefine(BaseModel):
    """Schema for refining an existing job."""

    prompt: str = Field(..., min_length=1, max_length=1000, description="Refinement prompt")


class JobCreateResponse(BaseModel):
    """Schema for job creation response."""

    job_id: UUID
    status: JobStatus
