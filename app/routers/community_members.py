# app/routers/community_members.py
#
# ──────────────────────────────────────────────────────────────────
# Community Members API
#
# PUBLIC (no login):
#   GET /community-members/job/{job_id}       → members for a job
#   GET /community-members/scheme/{scheme_id} → members for a scheme
#
# ADMIN ONLY:
#   POST   /community-members                 → add a member
#   DELETE /community-members/{id}            → remove a member
# ──────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.community_member import CommunityMember
from app.models.user import User
from app.schemas.community_member import CommunityMemberCreate, CommunityMemberResponse
from app.core.deps import require_admin
router = APIRouter(
    prefix="/community-members",
    tags=["Community Members"]
)
# ── PUBLIC ENDPOINTS ──────────────────────────────────────────────

@router.get("/job/{job_id}", response_model=List[CommunityMemberResponse])
def get_members_for_job(job_id: str, db: Session = Depends(get_db)):
    """
    Returns all members who applied for a specific Job Alert.
    Sorted by since_date ascending — earliest applicant first.
    No login required — visible to everyone.
    """
    return db.query(CommunityMember).filter(
        CommunityMember.job_id == job_id,
        CommunityMember.is_active == True
    ).order_by(CommunityMember.since_date.asc()).all()


@router.get("/scheme/{scheme_id}", response_model=List[CommunityMemberResponse])
def get_members_for_scheme(scheme_id: str, db: Session = Depends(get_db)):
    """
    Returns all members who are availing a specific Scheme.
    Sorted by since_date ascending — longest availing first.
    No login required — visible to everyone for social awareness.
    """
    return db.query(CommunityMember).filter(
        CommunityMember.scheme_id == scheme_id,
        CommunityMember.is_active == True
    ).order_by(CommunityMember.since_date.asc()).all()


# ── ADMIN ENDPOINTS ───────────────────────────────────────────────

@router.post("", response_model=CommunityMemberResponse, status_code=201)
def add_member(
    data: CommunityMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Admin adds a person to the members list of a Job or Scheme.
    The admin's ID is auto-recorded from their JWT token.
    """
    member = CommunityMember(
        **data.model_dump(),
        added_by_admin_id=current_user.id,  # ✅ auto-filled from token
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{member_id}", status_code=200)
def remove_member(
    member_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Admin removes a member entry — soft delete.
    Used to correct mistakes or remove outdated entries.
    """
    member = db.query(CommunityMember).filter(
        CommunityMember.id == member_id
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found.")

    # ✅ Soft delete — record stays in DB for audit
    member.is_active = False
    db.commit()
    return {"message": "Member removed successfully."}