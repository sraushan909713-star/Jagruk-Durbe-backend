# app/routers/schemes.py
# ─────────────────────────────────────────────
# This router handles all Government Schemes endpoints.
# Read endpoints are open to everyone (no login needed).
# Write endpoints (create/edit/delete) are restricted to Admin and Super Admin only.
# ─────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.scheme import Scheme, SchemeCategory
from app.models.user import User
from app.schemas.scheme import SchemeCreate, SchemeUpdate, SchemeResponse, SchemeListResponse
from app.core.deps import require_admin

router = APIRouter(
    prefix="/schemes",
    tags=["Government Schemes"]
)
# ─────────────────────────────────────────────
# PUBLIC ENDPOINTS (no login required)
# ─────────────────────────────────────────────

@router.get("", response_model=List[SchemeListResponse])
def list_schemes(
    category: Optional[SchemeCategory] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, description="Search by scheme name"),
    db: Session = Depends(get_db)
):
    """
    Returns a list of all active government schemes.
    Optionally filter by category or search by name.
    No login required — any villager can browse schemes.
    """
    query = db.query(Scheme).filter(Scheme.is_active == True)

    # Apply category filter if provided
    if category:
        query = query.filter(Scheme.category == category)

    # Apply name search if provided (case-insensitive)
    if search:
        query = query.filter(Scheme.name.ilike(f"%{search}%"))

    return query.all()


@router.get("/{scheme_id}", response_model=SchemeResponse)
def get_scheme(scheme_id: str, db: Session = Depends(get_db)):
    """
    Returns full details of a single scheme by its ID.
    No login required — any villager can view scheme details.
    """
    scheme = db.query(Scheme).filter(
        Scheme.id == scheme_id,
        Scheme.is_active == True
    ).first()

    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found.")

    return scheme


# ─────────────────────────────────────────────
# ADMIN-ONLY ENDPOINTS (login + admin role required)
# ─────────────────────────────────────────────

@router.post("", response_model=SchemeResponse, status_code=201)
def create_scheme(
    data: SchemeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)   # ← blocks non-admins
):
    """
    Creates a new government scheme.
    Only Admins and Super Admins can do this.
    """
    scheme = Scheme(
        name=data.name,
        description=data.description,
        eligibility=data.eligibility,
        how_to_apply=data.how_to_apply,
        category=data.category,
        official_link=data.official_link,
        youtube_link=data.youtube_link,                                              # ✅ ADD
        documents_required=data.documents_required,                                  # ✅ ADD
        additional_info=data.additional_info
    )
    db.add(scheme)
    db.commit()
    db.refresh(scheme)
    return scheme


@router.put("/{scheme_id}", response_model=SchemeResponse)
def update_scheme(
    scheme_id: str,
    data: SchemeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)   # ← blocks non-admins
):
    """
    Updates an existing scheme.
    Only sends fields that need to change — everything else stays the same.
    Only Admins and Super Admins can do this.
    """
    scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()

    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found.")

    # Only update fields that were actually sent in the request
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(scheme, field, value)

    db.commit()
    db.refresh(scheme)
    return scheme


@router.delete("/{scheme_id}", status_code=200)
def delete_scheme(
    scheme_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)   # ← blocks non-admins
):
    """
    Soft-deletes a scheme by setting is_active = False.
    The scheme is hidden from villagers but NOT removed from the database.
    This preserves data history.
    Only Admins and Super Admins can do this.
    """
    scheme = db.query(Scheme).filter(Scheme.id == scheme_id).first()

    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found.")

    scheme.is_active = False
    db.commit()
    return {"message": "Scheme deactivated successfully."}