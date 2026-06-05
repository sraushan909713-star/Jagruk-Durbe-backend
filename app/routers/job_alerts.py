# app/routers/job_alerts.py
#
# ──────────────────────────────────────────────────────────────────
# Job Alerts API — Sarkari Naukri for Durbe village youth.
#
# PUBLIC (no login required):
#   GET  /job-alerts                          → list all active jobs
#   GET  /job-alerts/{id}                     → full job detail
#   GET  /job-alerts/{id}/applicants          → social proof list
#
# ADMIN ONLY (Admin or Super Admin):
#   POST   /job-alerts                        → add new job posting
#   PUT    /job-alerts/{id}                   → edit job posting
#   DELETE /job-alerts/{id}                   → soft delete job
#   POST   /job-alerts/{id}/applicants        → add applicant (after WhatsApp proof)
#   DELETE /job-alerts/{id}/applicants/{aid}  → remove applicant
# ──────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.job_alert import JobAlert, JobApplicant, JobCategory
from app.models.user import User
from app.schemas.job_alert import (
    JobAlertCreate, JobAlertUpdate,
    JobAlertListResponse, JobAlertResponse,
    JobApplicantCreate, JobApplicantResponse
)
from app.core.deps import require_admin
router = APIRouter(
    prefix="/job-alerts",
    tags=["Job Alerts"]
)
# ─── PUBLIC ENDPOINTS ────────────────────────────────────────────

@router.get("", response_model=List[JobAlertListResponse])
def list_jobs(
    category: Optional[JobCategory] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db)
):
    """
    Returns all active job alerts.
    Sorted by last_date ascending — closest deadline first.
    No login required.
    """
    query = db.query(JobAlert).filter(JobAlert.is_active == True)
    if category:
        query = query.filter(JobAlert.category == category)
    return query.order_by(JobAlert.last_date.asc()).all()


@router.get("/{job_id}", response_model=JobAlertResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Full detail of a single job alert. No login required."""
    job = db.query(JobAlert).filter(
        JobAlert.id == job_id,
        JobAlert.is_active == True
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job alert not found.")
    return job


@router.get("/{job_id}/applicants", response_model=List[JobApplicantResponse])
def list_applicants(job_id: str, db: Session = Depends(get_db)):
    """
    Returns all active applicants for a job — social proof section.
    Villagers see who from Durbe has already applied.
    No login required.
    """
    job = db.query(JobAlert).filter(
        JobAlert.id == job_id,
        JobAlert.is_active == True
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job alert not found.")

    return db.query(JobApplicant).filter(
        JobApplicant.job_id  == job_id,
        JobApplicant.is_active == True
    ).order_by(JobApplicant.created_at.desc()).all()


# ─── ADMIN ENDPOINTS — Job management ────────────────────────────

@router.post("", response_model=JobAlertResponse, status_code=201)
def create_job(
    data: JobAlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Admin adds a new job alert."""
    job = JobAlert(**data.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.put("/{job_id}", response_model=JobAlertResponse)
def update_job(
    job_id: str,
    data: JobAlertUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Admin updates a job alert — only provided fields are changed."""
    job = db.query(JobAlert).filter(
        JobAlert.id == job_id,
        JobAlert.is_active == True
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job alert not found.")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(job, field, value)

    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=200)
def delete_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Soft deletes a job alert — sets is_active=False."""
    job = db.query(JobAlert).filter(JobAlert.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job alert not found.")
    job.is_active = False
    db.commit()
    return {"message": "Job alert removed successfully."}


# ─── ADMIN ENDPOINTS — Applicant management ──────────────────────

@router.post("/{job_id}/applicants", response_model=JobApplicantResponse, status_code=201)
def add_applicant(
    job_id: str,
    data: JobApplicantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Admin adds a villager to the applicant list after verifying
    their WhatsApp proof. Works for both Gram Seva users and
    non-app villagers (gram_seva_user_id is optional).
    """
    job = db.query(JobAlert).filter(
        JobAlert.id == job_id,
        JobAlert.is_active == True
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job alert not found.")

    applicant = JobApplicant(
        job_id            = job_id,
        name              = data.name,
        relative_name     = data.relative_name,
        gender            = data.gender,
        photo_url         = data.photo_url,
        gram_seva_user_id = data.gram_seva_user_id,
        applied_date      = data.applied_date,
    )
    db.add(applicant)
    db.commit()
    db.refresh(applicant)
    return applicant


@router.delete("/{job_id}/applicants/{applicant_id}", status_code=200)
def remove_applicant(
    job_id:       str,
    applicant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Admin removes an applicant entry (moderation)."""
    applicant = db.query(JobApplicant).filter(
        JobApplicant.id     == applicant_id,
        JobApplicant.job_id == job_id
    ).first()
    if not applicant:
        raise HTTPException(status_code=404, detail="Applicant not found.")
    applicant.is_active = False
    db.commit()
    return {"message": "Applicant removed successfully."}