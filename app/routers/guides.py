# app/routers/guides.py
# ─────────────────────────────────────────────────────────────
# Documentation Guides API
#
# PUBLIC (no login required):
#   GET  /guides/       → list all active guides (filter by category)
#   GET  /guides/{id}   → full step-by-step detail
#
# ADMIN ONLY:
#   POST   /guides/       → add a new guide
#   PUT    /guides/{id}   → edit a guide
#   DELETE /guides/{id}   → soft delete
# ─────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.guide import Guide, GuideCategory
from app.models.user import User
from app.schemas.guide import (
    GuideCreate, GuideUpdate, GuideResponse, GuideListResponse
)
from app.core.deps import require_admin
router = APIRouter(prefix="/guides", tags=["Documentation Guides"])
# ─── Public Endpoints ─────────────────────────────────────────

@router.get("/", response_model=List[GuideListResponse])
def get_all_guides(
    category: Optional[GuideCategory] = Query(None),
    village_id: str = Query("1"),
    db: Session = Depends(get_db)
):
    """
    Returns all active guides. Optionally filter by category.
    Sorted by category then title for easy browsing.
    No login required.
    """
    query = db.query(Guide).filter(
        Guide.is_active  == True,
        Guide.village_id == village_id
    )
    if category:
        query = query.filter(Guide.category == category)
    return query.order_by(Guide.category, Guide.title).all()


@router.get("/{guide_id}", response_model=GuideResponse)
def get_guide(guide_id: str, db: Session = Depends(get_db)):
    """Full detail of a single guide. No login required."""
    guide = db.query(Guide).filter(
        Guide.id == guide_id,
        Guide.is_active == True
    ).first()
    if not guide:
        raise HTTPException(status_code=404, detail="Guide not found.")
    return guide


# ─── Admin Endpoints ──────────────────────────────────────────

@router.post("/", response_model=GuideResponse)
def create_guide(
    data: GuideCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Admin adds a new documentation guide."""
    guide = Guide(**data.model_dump())
    db.add(guide)
    db.commit()
    db.refresh(guide)
    return guide


@router.put("/{guide_id}", response_model=GuideResponse)
def update_guide(
    guide_id: str,
    data: GuideUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Admin updates a guide — only sent fields are changed."""
    guide = db.query(Guide).filter(
        Guide.id == guide_id,
        Guide.is_active == True
    ).first()
    if not guide:
        raise HTTPException(status_code=404, detail="Guide not found.")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(guide, field, value)
    db.commit()
    db.refresh(guide)
    return guide


@router.delete("/{guide_id}")
def delete_guide(
    guide_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Soft deletes a guide — sets is_active=False."""
    guide = db.query(Guide).filter(
        Guide.id == guide_id,
        Guide.is_active == True
    ).first()
    if not guide:
        raise HTTPException(status_code=404, detail="Guide not found.")
    guide.is_active = False
    db.commit()
    return {"message": f"Guide '{guide.title}' deleted successfully."}
