import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import async_session, get_db
from app.models import Job, JobStatus
from app.schemas import (
    GenerateLeadsRequest,
    GenerateLeadsResponse,
    JobStatusResponse,
    LeadOut,
)
from app.services.lead_pipeline import run_pipeline

router = APIRouter(prefix="/api", tags=["leads"])


@router.post("/generate-leads", response_model=GenerateLeadsResponse)
async def generate_leads(req: GenerateLeadsRequest, db: AsyncSession = Depends(get_db)):
    bounds_dict = {
        "low": {"latitude": req.bounds.low.latitude, "longitude": req.bounds.low.longitude},
        "high": {"latitude": req.bounds.high.latitude, "longitude": req.bounds.high.longitude},
    }

    job = Job(
        sector=req.sector,
        bounds_json=json.dumps(bounds_dict),
        portfolio_url=req.portfolio_url,
        city=req.city,
        status=JobStatus.PENDING,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Launch pipeline as a background task
    asyncio.create_task(
        run_pipeline(
            job_id=job.id,
            sector=req.sector,
            bounds=bounds_dict,
            portfolio_url=req.portfolio_url,
            session_factory=async_session,
        )
    )

    return GenerateLeadsResponse(job_id=job.id)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Job).options(selectinload(Job.leads)).where(Job.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    leads = [
        LeadOut(
            business_name=lead.business_name,
            website=lead.website,
            email_found=lead.email_found,
            reviews=lead.review_count,
            ai_email_draft=lead.ai_email_draft,
        )
        for lead in job.leads
    ]

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        city=job.city,
        leads=leads,
        sector=job.sector,
        error_message=job.error_message,
    )

@router.get("/jobs", response_model=list[JobStatusResponse])
async def list_jobs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).options(selectinload(Job.leads)).order_by(Job.created_at.desc()))
    jobs = result.scalars().all()

    job_responses = []
    for job in jobs:
        leads = [
            LeadOut(
                business_name=lead.business_name,
                website=lead.website,
                email_found=lead.email_found,
                reviews=lead.review_count,
                ai_email_draft=lead.ai_email_draft,
            )
            for lead in job.leads
        ]

        job_responses.append(
            JobStatusResponse(
                job_id=job.id,
                status=job.status,
                city=job.city,
                leads=leads,
                sector=job.sector,
                error_message=job.error_message,
            )
        )

    return job_responses
