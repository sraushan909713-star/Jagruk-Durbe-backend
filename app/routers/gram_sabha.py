# app/routers/gram_sabha.py
# ─────────────────────────────────────────────
# Gram Sabha — Official Village Assembly Records
# Read endpoints open to everyone.
# Write endpoints restricted to Admin and Super Admin only.
# These are official records — not user-generated content.
# ─────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.gram_sabha import GramSabha
from app.models.user import User
from app.schemas.gram_sabha import (
    GramSabhaCreate, GramSabhaUpdate,
    GramSabhaResponse, GramSabhaListResponse
)
from app.core.deps import require_admin
router = APIRouter(
    prefix="/gram-sabha",
    tags=["Gram Sabha"]
)
# ─────────────────────────────────────────────
# PUBLIC ENDPOINTS
# ─────────────────────────────────────────────

@router.get("", response_model=List[GramSabhaListResponse])
def list_records(db: Session = Depends(get_db)):
    """
    Returns all active Gram Sabha records.
    Sorted by meeting date — most recent first.
    No login required — any villager can view meeting records.
    """
    return db.query(GramSabha).filter(
        GramSabha.is_active == True
    ).order_by(GramSabha.meeting_date.desc()).all()


@router.get("/{record_id}", response_model=GramSabhaResponse)
def get_record(record_id: str, db: Session = Depends(get_db)):
    """
    Returns full details of a single Gram Sabha meeting record.
    No login required.
    """
    record = db.query(GramSabha).filter(
        GramSabha.id == record_id,
        GramSabha.is_active == True
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")

    return record


# ─────────────────────────────────────────────
# ADMIN-ONLY ENDPOINTS
# ─────────────────────────────────────────────

@router.post("", response_model=GramSabhaResponse, status_code=201)
def create_record(
    data: GramSabhaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Adds a new Gram Sabha meeting record.
    Only Admins and Super Admins can add official records.
    """
    record = GramSabha(
        title=data.title,
        meeting_date=data.meeting_date,
        location=data.location,
        agenda=data.agenda,
        decisions=data.decisions,
        attendees_count=data.attendees_count,
        minutes_url=data.minutes_url,
        created_by=current_user.id
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.put("/{record_id}", response_model=GramSabhaResponse)
def update_record(
    record_id: str,
    data: GramSabhaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Updates an existing Gram Sabha record.
    Only Admins and Super Admins can edit records.
    """
    record = db.query(GramSabha).filter(GramSabha.id == record_id).first()

    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return record


@router.delete("/{record_id}", status_code=200)
def delete_record(
    record_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Soft-deletes a Gram Sabha record.
    Only Admins and Super Admins can do this.
    """
    record = db.query(GramSabha).filter(GramSabha.id == record_id).first()

    if not record:
        raise HTTPException(status_code=404, detail="Record not found.")

    record.is_active = False
    db.commit()
    return {"message": "Record removed successfully."}