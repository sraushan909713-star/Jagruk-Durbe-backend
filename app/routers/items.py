# app/routers/items.py
# ─────────────────────────────────────────────────────────────
# API endpoints for the items master catalog.
#
# PUBLIC (no login):
#   GET  /items/               → all active items, sorted by display_order
#   GET  /items/{id}           → single item
#
# VENDOR + ADMIN (JWT required):
#   POST /items/               → create new item
#                                (is_custom auto-set: True if vendor, False if admin)
#
# ADMIN ONLY:
#   PUT    /items/{id}         → edit item (typos, display_order, default unit)
#   DELETE /items/{id}         → soft delete
#                                Blocked if any active vendor_listings reference it.
# ─────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.item import Item
from app.models.vendor_listing import VendorListing
from app.models.user import User, UserRole
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse
from app.core.deps import require_admin, require_vendor_or_admin
router = APIRouter(prefix="/items", tags=["Items — Mandi Catalog"])
# ─────────────────────────────────────────────────────────────
# PUBLIC ENDPOINTS
# ─────────────────────────────────────────────────────────────

@router.get("/", response_model=List[ItemResponse])
def list_items(db: Session = Depends(get_db)):
    """
    Returns all active items, sorted by display_order ascending,
    then by name. Drives the curated home-screen order.
    """
    return (
        db.query(Item)
        .filter(Item.is_active == True)
        .order_by(Item.display_order.asc(), Item.name.asc())
        .all()
    )


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: str, db: Session = Depends(get_db)):
    item = db.query(Item).filter(
        Item.id == item_id, Item.is_active == True
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")
    return item


# ─────────────────────────────────────────────────────────────
# VENDOR + ADMIN: CREATE
# ─────────────────────────────────────────────────────────────

@router.post("/", response_model=ItemResponse)
def create_item(
    data: ItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_vendor_or_admin)
):
    """
    Vendor or admin creates a new item.
    Goes live immediately — no moderation queue.
    is_custom = True if requester is vendor, False if admin/super_admin.
    """
    is_custom = current_user.role == UserRole.vendor

    item = Item(
        **data.model_dump(),
        is_custom=is_custom,
        created_by_vendor_id=current_user.id if is_custom else None,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# ─────────────────────────────────────────────────────────────
# ADMIN ONLY: EDIT / DELETE
# ─────────────────────────────────────────────────────────────

@router.put("/{item_id}", response_model=ItemResponse)
def update_item(
    item_id: str,
    data: ItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Admin only. Fixes typos, updates display_order, changes default unit.
    """
    item = db.query(Item).filter(
        Item.id == item_id, Item.is_active == True
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}")
def delete_item(
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Admin only. Soft delete.
    Blocked if any active vendor_listings reference this item —
    admin must remove those listings first (their delete power
    covers listings too).
    """
    item = db.query(Item).filter(
        Item.id == item_id, Item.is_active == True
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")

    # Block delete if listings reference it
    listing_count = db.query(VendorListing).filter(
        VendorListing.item_id == item_id,
        VendorListing.is_active == True
    ).count()

    if listing_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete: {listing_count} active listings use this item. Remove them first."
        )

    item.is_active = False
    db.commit()
    return {"message": f"Item '{item.name}' deleted."}