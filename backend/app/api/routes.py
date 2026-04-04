import asyncio
from pathlib import Path
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import router as auth_router
from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.job import Job, JobStatus
from app.models.user import User
from app.schemas.animation import AnimationPlan
from app.schemas.job import JobCreate, JobCreateResponse, JobRefine, JobResponse, JobUpdate
from app.services.llm import refine_plan
from app.worker.tasks import render_custom_code_task, render_graph_task

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["auth"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "AnimaStudio API"}


@router.post("/jobs", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new rendering job.

    Accepts a prompt and queues a Celery task to render the graph.
    """
    # Create job in database
    job = Job(prompt=job_data.prompt, status=JobStatus.QUEUED, owner_id=current_user.id)
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Queue Celery task
    render_graph_task.delay(str(job.id))

    return JobCreateResponse(job_id=job.id, status=job.status)


@router.get("/jobs", response_model=list[JobResponse])
async def list_jobs(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    List all jobs for the current user.
    """
    result = await db.execute(
        select(Job).where(Job.owner_id == current_user.id).order_by(Job.created_at.desc())
    )
    jobs = result.scalars().all()
    return jobs


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Get job status and details.

    Returns the current status, video filename (if completed), code, logs, and error.
    """
    result = await db.execute(select(Job).where(Job.id == job_id, Job.owner_id == current_user.id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")

    return JobResponse.model_validate(job)


@router.post("/jobs/{job_id}/refine", response_model=JobCreateResponse)
async def refine_job(
    job_id: UUID,
    refine_data: JobRefine,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Refine an existing rendering job.
    """
    # 1. Get original job
    result = await db.execute(select(Job).where(Job.id == job_id, Job.owner_id == current_user.id))
    original_job = result.scalar_one_or_none()

    if not original_job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")

    # 2. Get original plan
    if not original_job.plan_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Job has no plan to refine"
        )

    original_plan = AnimationPlan.model_validate(original_job.plan_json)

    # 3. Refine plan using LLM
    refined_plan = refine_plan(original_job.prompt, original_plan, refine_data.prompt)

    # 4. Create new job for refined animation
    new_job = Job(
        prompt=f"Refinement of {job_id}: {refine_data.prompt}",
        status=JobStatus.QUEUED,
        owner_id=current_user.id,
        plan_json=refined_plan.model_dump(),
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    # 5. Queue Celery task (using the pre-generated refined plan)
    render_graph_task.delay(str(new_job.id))

    return JobCreateResponse(job_id=new_job.id, status=new_job.status)


@router.patch("/jobs/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: UUID,
    job_update: JobUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update job code and re-render.
    """
    result = await db.execute(select(Job).where(Job.id == job_id, Job.owner_id == current_user.id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")

    if job_update.code:
        job.code = job_update.code
        job.status = JobStatus.QUEUED
        await db.commit()
        await db.refresh(job)

        # Queue custom code rendering
        render_custom_code_task.delay(str(job.id))

    return JobResponse.model_validate(job)


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Delete a job and its associated video.
    """
    result = await db.execute(select(Job).where(Job.id == job_id, Job.owner_id == current_user.id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found")

    # Delete video file if it exists
    if job.video_filename:
        video_path = Path(settings.OUTPUTS_DIR) / job.video_filename
        if video_path.exists():
            video_path.unlink()

    await db.delete(job)
    await db.commit()

    return {"status": "success"}


@router.get("/videos/{filename}")
async def get_video(filename: str):
    """
    Serve rendered video files.

    Returns the video file from the outputs directory.
    """
    # Sanitize filename to prevent directory traversal
    safe_filename = Path(filename).name
    video_path = Path(settings.OUTPUTS_DIR) / safe_filename

    if not video_path.exists() or not video_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Video {filename} not found"
        )

    # Verify it's an mp4 file
    if video_path.suffix.lower() != ".mp4":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file type")

    return FileResponse(path=video_path, media_type="video/mp4", filename=safe_filename)


@router.get("/jobs/{job_id}/logs/stream")
async def stream_job_logs(job_id: UUID):
    channel = f"logs:{job_id}"
    r = aioredis.from_url(settings.REDIS_URL)
    pubsub = r.pubsub()
    await pubsub.subscribe(channel)

    async def event_generator():
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
                if message:
                    data = message.get("data")
                    if isinstance(data, bytes):
                        data = data.decode()
                    yield f"data: {data}\n\n"
                else:
                    await asyncio.sleep(0.1)
        finally:
            await pubsub.unsubscribe(channel)
            await r.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
