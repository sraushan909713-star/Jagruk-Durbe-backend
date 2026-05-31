# app/routers/units.py
# ─────────────────────────────────────────────────────────────
# API endpoints for the units master table.
# Same pattern as items.py — public read, vendor/admin create,
# admin-only edit/delete with reference check.
# ─────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.unit import Unit
from app.models.vendor_listing import VendorListing
from app.models.user import User, UserRole
from app.schemas.unit import UnitCreate, UnitUpdate, UnitResponse
from app.core.security import decode_access_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/units", tags=["Units — Mandi Catalog"])

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


def require_vendor_or_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in [UserRole.vendor, UserRole.admin, UserRole.super_admin]:
        raise HTTPException(status_code=403, detail="Only vendors or admins can add units.")
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in [UserRole.admin, UserRole.super_admin]:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user


# ─────────────────────────────────────────────────────────────
# PUBLIC ENDPOINTS
# ─────────────────────────────────────────────────────────────

@router.get("/", response_model=List[UnitResponse])
def list_units(db: Session = Depends(get_db)):
    return (
        db.query(Unit)
        .filter(Unit.is_active == True)
        .order_by(Unit.is_custom.asc(), Unit.name.asc())
        .all()
    )


@router.get("/{unit_id}", response_model=UnitResponse)
def get_unit(unit_id: str, db: Session = Depends(get_db)):
    unit = db.query(Unit).filter(
        Unit.id == unit_id, Unit.is_active == True
    ).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found.")
    return unit


# ─────────────────────────────────────────────────────────────
# VENDOR + ADMIN: CREATE
# ─────────────────────────────────────────────────────────────

@router.post("/", response_model=UnitResponse)
def create_unit(
    data: UnitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_vendor_or_admin)
):
    """
    Vendor or admin creates a new unit. Goes live immediately.
    """
    # Prevent duplicate active units with the same name
    existing = db.query(Unit).filter(
        Unit.name == data.name, Unit.is_active == True
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Unit '{data.name}' already exists.")

    is_custom = current_user.role == UserRole.vendor

    unit = Unit(
        **data.model_dump(),
        is_custom=is_custom,
        created_by_vendor_id=current_user.id if is_custom else None,
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


# ─────────────────────────────────────────────────────────────
# ADMIN ONLY: EDIT / DELETE
# ─────────────────────────────────────────────────────────────

@router.put("/{unit_id}", response_model=UnitResponse)
def update_unit(
    unit_id: str,
    data: UnitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    unit = db.query(Unit).filter(
        Unit.id == unit_id, Unit.is_active == True
    ).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found.")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(unit, field, value)

    db.commit()
    db.refresh(unit)
    return unit


@router.delete("/{unit_id}")
def delete_unit(
    unit_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    unit = db.query(Unit).filter(
        Unit.id == unit_id, Unit.is_active == True
    ).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found.")

    listing_count = db.query(VendorListing).filter(
        VendorListing.unit_id == unit_id,
        VendorListing.is_active == True
    ).count()

    if listing_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: {listing_count} active listings use this unit."
        )

    unit.is_active = False
    db.commit()
    return {"message": f"Unit '{unit.name}' deleted."}