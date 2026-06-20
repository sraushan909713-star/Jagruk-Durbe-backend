# app/routers/vendor_listings.py
# ─────────────────────────────────────────────────────────────
# API endpoints for Vendor Listings (Mandi Prices).
#
# PUBLIC (no login):
#   GET  /vendor-listings/         → all active listings (joined with item/unit names)
#                                    Filters: mode, vendor_id, item_id, max_age_days
#   GET  /vendor-listings/{id}     → single listing
#
# VENDOR ONLY (JWT, role=vendor):
#   GET    /vendor-listings/my/    → vendor's own listings only
#   POST   /vendor-listings/       → create new listing
#   PUT    /vendor-listings/{id}   → update price/unit/stock/notes
#                                    (item_id and mode LOCKED — creator-only edit)
#
# VENDOR (own) + ADMIN (any):
#   DELETE /vendor-listings/{id}   → soft delete
#
# Golden rule enforced: admin can DELETE any but cannot EDIT
# someone else's content.
# ─────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models.vendor_listing import VendorListing, TradeMode
from app.models.item import Item
from app.models.unit import Unit
from app.models.user import User, UserRole
from app.schemas.vendor_listing import (
    VendorListingCreate, VendorListingUpdate, VendorListingResponse
)
from app.models.price_history import PriceHistory
from app.core.deps import require_vendor_or_admin
router = APIRouter(
    prefix="/vendor-listings",
    tags=["Vendor Listings — Mandi Prices"]
)

# ── Record a price event into history ────────────────────────
# Called on create and on every price change. No cron — these
# event rows are all we need; the chart connects them.
def _record_price(db: Session, listing: VendorListing) -> None:
    db.add(PriceHistory(
        item_id   = listing.item_id,
        vendor_id = listing.vendor_id,
        mode      = listing.mode.value if hasattr(listing.mode, 'value') else listing.mode,
        price     = listing.price,
    ))

def _serialize_with_joins(listing: VendorListing, item: Optional[Item], unit: Optional[Unit], vendor_user: Optional[User],) -> dict:
    """
    Build the response payload with joined item and unit names.
    Used by all GET endpoints so Flutter never needs a second fetch.
    """
    return {
        "id": listing.id,
        "village_id": listing.village_id,
        "vendor_id": listing.vendor_id,
        "vendor_name": listing.vendor_name,
        "vendor_phone": vendor_user.phone if vendor_user else None,
        "item_id": listing.item_id,
        "item_name": item.name if item else None,
        "item_name_hindi": item.name_hindi if item else None,
        "unit_id": listing.unit_id,
        "unit_name": unit.name if unit else None,
        "unit_name_hindi": unit.name_hindi if unit else None,
        "mode": listing.mode,
        "price": listing.price,
        "stock_status": listing.stock_status,
        "notes": listing.notes,
        "is_active": listing.is_active,
        "created_at": listing.created_at,
        "updated_at": listing.updated_at,
    }


def _fetch_listings(
    db: Session,
    *,
    mode: Optional[TradeMode] = None,
    vendor_id: Optional[str] = None,
    item_id: Optional[str] = None,
    village_id: str = "1",
    max_age_days: Optional[int] = None,
    only_vendor: Optional[str] = None,
) -> List[dict]:
    """
    Shared query builder + serializer for all listing GET endpoints.
    """
    q = db.query(VendorListing, Item, Unit, User).outerjoin(            # ✅ join User
        Item, VendorListing.item_id == Item.id
    ).outerjoin(
        Unit, VendorListing.unit_id == Unit.id
    ).outerjoin(
        User, VendorListing.vendor_id == User.id                        # ✅ NEW
    ).filter(
        VendorListing.is_active == True,
        VendorListing.village_id == village_id,
    )

    if mode:
        q = q.filter(VendorListing.mode == mode)
    if vendor_id:
        q = q.filter(VendorListing.vendor_id == vendor_id)
    if item_id:
        q = q.filter(VendorListing.item_id == item_id)
    if only_vendor:
        q = q.filter(VendorListing.vendor_id == only_vendor)
    if max_age_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        q = q.filter(VendorListing.updated_at >= cutoff)

    # Freshest first
    q = q.order_by(VendorListing.updated_at.desc())

    return [_serialize_with_joins(lst, i, u, vu) for (lst, i, u, vu) in q.all()]   # ✅


# ─────────────────────────────────────────────────────────────
# PUBLIC GETS
# ─────────────────────────────────────────────────────────────

@router.get("/", response_model=List[VendorListingResponse])
def list_listings(
    mode: Optional[TradeMode] = Query(None, description="Filter: buy / sell"),
    vendor_id: Optional[str] = Query(None, description="Filter: specific vendor"),
    item_id: Optional[str] = Query(None, description="Filter: specific item"),
    village_id: str = Query("1"),
    max_age_days: int = Query(14, description="Drop entries older than this many days. Default 14 for the freshness cutoff."),
    db: Session = Depends(get_db),
):
    """
    Public read. The default 14-day filter implements the freshness cutoff
    — listings older than 14 days are hidden from villagers entirely.
    Pass max_age_days=0 (or a large number) to bypass for admin views.
    """
    return _fetch_listings(
        db,
        mode=mode,
        vendor_id=vendor_id,
        item_id=item_id,
        village_id=village_id,
        max_age_days=max_age_days if max_age_days > 0 else None,
    )


@router.get("/my/", response_model=List[VendorListingResponse])
def list_my_listings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_vendor_or_admin),
):
    """
    Vendor's own listings only.
    Powers the "Manage My Listings" screen.
    Returns ALL of vendor's listings regardless of age — no freshness cutoff —
    because vendor needs to see stale entries to update them.
    """
    return _fetch_listings(db, only_vendor=current_user.id)


@router.get("/{listing_id}", response_model=VendorListingResponse)
def get_listing(listing_id: str, db: Session = Depends(get_db)):
    row = (
        db.query(VendorListing, Item, Unit, User)                       # ✅
        .outerjoin(Item, VendorListing.item_id == Item.id)
        .outerjoin(Unit, VendorListing.unit_id == Unit.id)
        .outerjoin(User, VendorListing.vendor_id == User.id)            # ✅ NEW
        .filter(VendorListing.id == listing_id, VendorListing.is_active == True)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Listing not found.")
    listing, item, unit, vendor_user = row                              # ✅
    return _serialize_with_joins(listing, item, unit, vendor_user)      # ✅

@router.get("/history/{item_id}")
def get_price_history(
    item_id: str,
    mode: TradeMode = Query(...),
    db: Session = Depends(get_db),
):
    """
    Price trend for one item on one side (buy/sell).
    Returns every recorded price event, oldest first, with the
    vendor it belongs to. The Flutter side builds:
      • the village line  = best price per day (lowest for sell,
        highest for buy) across vendors
      • per-vendor lines  = one vendor's own points
    Flat stretches are drawn by connecting points — no faked rows.
    """
    mode_str = mode.value if hasattr(mode, 'value') else mode
    rows = db.query(PriceHistory).filter(
        PriceHistory.item_id == item_id,
        PriceHistory.mode == mode_str,
    ).order_by(PriceHistory.recorded_at.asc()).all()

    # vendor names (for per-vendor lines) — one lookup, not per row
    vendor_ids = {r.vendor_id for r in rows}
    vendors = {}
    if vendor_ids:
        for u in db.query(User).filter(User.id.in_(vendor_ids)).all():
            vendors[u.id] = u.shop_name or u.full_name

    return [
        {
            "vendor_id":   r.vendor_id,
            "vendor_name": vendors.get(r.vendor_id, "—"),
            "price":       r.price,
            "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
        }
        for r in rows
    ]


# ─────────────────────────────────────────────────────────────
# VENDOR WRITES
# ─────────────────────────────────────────────────────────────

@router.post("/", response_model=VendorListingResponse)
def create_listing(
    data: VendorListingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_vendor_or_admin),
):
    """
    Vendor creates a new listing.
    Enforces the unique constraint (vendor_id, item_id, mode) at the app level
    with a friendly error before the DB throws an integrity error.
    """
    # Validate item and unit exist and are active
    item = db.query(Item).filter(Item.id == data.item_id, Item.is_active == True).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found.")
    unit = db.query(Unit).filter(Unit.id == data.unit_id, Unit.is_active == True).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found.")

    # Check for existing active listing with same (vendor, item, mode)
    existing = db.query(VendorListing).filter(
        VendorListing.vendor_id == current_user.id,
        VendorListing.item_id == data.item_id,
        VendorListing.mode == data.mode,
        VendorListing.is_active == True,
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"You already have a {data.mode.value} listing for this item. Update the existing one instead."
        )

    listing = VendorListing(
        **data.model_dump(),
        vendor_id=current_user.id,
        vendor_name=current_user.shop_name or current_user.full_name,
    )
    db.add(listing)
    db.flush()              # get listing fields populated before snapshot
    _record_price(db, listing)   # ✅ first price point
    db.commit()
    db.refresh(listing)
    return _serialize_with_joins(listing, item, unit, current_user)     # ✅ vendor is the creator


@router.put("/{listing_id}", response_model=VendorListingResponse)
def update_listing(
    listing_id: str,
    data: VendorListingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_vendor_or_admin),
):
    """
    Update price / unit / stock / notes.
    item_id and mode are NOT updatable — schema enforces this.
    Creator-only edit per golden rule: admin cannot edit other vendors' listings.
    """
    listing = db.query(VendorListing).filter(
        VendorListing.id == listing_id,
        VendorListing.is_active == True,
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found.")

    # ✅ Golden rule: creator-only edit. Admin can DELETE but not edit.
    if listing.vendor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only edit your own listings."
        )

    # Did the price actually change? Only snapshot if so.
    updates = data.model_dump(exclude_unset=True)
    price_changed = 'price' in updates and updates['price'] != listing.price

    for field, value in updates.items():
        setattr(listing, field, value)

    if price_changed:
        _record_price(db, listing)   # ✅ new price point

    db.commit()
    db.refresh(listing)

    item = db.query(Item).filter(Item.id == listing.item_id).first()
    unit = db.query(Unit).filter(Unit.id == listing.unit_id).first()
    vendor_user = db.query(User).filter(User.id == listing.vendor_id).first()  # ✅ NEW
    return _serialize_with_joins(listing, item, unit, vendor_user)             # ✅


@router.delete("/{listing_id}")
def delete_listing(
    listing_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_vendor_or_admin),
):
    """
    Soft delete. Vendor can delete own; admin/super_admin can delete any.
    """
    listing = db.query(VendorListing).filter(
        VendorListing.id == listing_id,
        VendorListing.is_active == True,
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found.")

    # Vendor can only delete own; admin/super_admin can delete any
    if current_user.role == UserRole.vendor and listing.vendor_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own listings."
        )

    listing.is_active = False
    db.commit()
    return {"message": "Listing deleted."}

@router.get("/vendors/")
def list_active_vendors(
    village_id: str = Query("1"),
    db: Session = Depends(get_db),
):
    """
    Public endpoint — returns distinct vendors with at least one
    active listing in this village. Used by the vendor filter on
    the Mandi home screen for ALL users (villagers, vendors, admins).
    Only includes vendors with active listings, so the filter never
    shows a vendor who has nothing to filter for.
    """
    # Get unique vendor_ids that currently have active listings
    vendor_ids_subq = (
        db.query(VendorListing.vendor_id)
        .filter(
            VendorListing.is_active == True,
            VendorListing.village_id == village_id,
        )
        .distinct()
        .subquery()
    )

    # Fetch full User records for those vendors
    users = (
        db.query(User)
        .filter(User.id.in_(vendor_ids_subq))
        .all()
    )

    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "phone": u.phone,
            "shop_name": u.shop_name,
        }
        for u in users
    ]