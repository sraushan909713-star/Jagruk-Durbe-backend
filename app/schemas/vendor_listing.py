# app/schemas/vendor_listing.py
# ─────────────────────────────────────────────────────────────
# Pydantic schemas for vendor listings API.
#
# VendorListingCreate   → vendor posts a new listing
# VendorListingUpdate   → vendor updates price/unit/stock/notes
#                         (item_id and mode are LOCKED after create —
#                          if vendor wants a different item, they
#                          create a new listing and delete the old)
# VendorListingResponse → what the app receives, with joined fields
# ─────────────────────────────────────────────────────────────

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.vendor_listing import TradeMode, StockStatus


# — REQUEST SCHEMAS ───────────────────────────────────────────

class VendorListingCreate(BaseModel):
    """
    Vendor creates a new listing.
    vendor_id and vendor_name are taken from JWT — not sent manually.
    """
    item_id: str
    unit_id: str
    mode: TradeMode
    price: float
    stock_status: StockStatus = StockStatus.in_stock
    notes: Optional[str] = None
    village_id: str = "1"


class VendorListingUpdate(BaseModel):
    """
    Vendor updates an existing listing.
    Most common use: just send {"price": 47} for a daily price refresh.
    item_id and mode are NOT updatable — locked after create.
    """
    unit_id: Optional[str] = None
    price: Optional[float] = None
    stock_status: Optional[StockStatus] = None
    notes: Optional[str] = None


# — RESPONSE SCHEMA ───────────────────────────────────────────

class VendorListingResponse(BaseModel):
    """
    Returned with the joined item and unit names so Flutter doesn't
    need to fetch the catalog separately for every listing.
    """
    id: str
    village_id: str
    vendor_id: str
    vendor_name: str
    vendor_phone: Optional[str]
    item_id: str
    item_name: Optional[str]            # joined from items.name
    item_name_hindi: Optional[str]      # joined from items.name_hindi
    unit_id: str
    unit_name: Optional[str]            # joined from units.name
    unit_name_hindi: Optional[str]      # joined from units.name_hindi
    mode: TradeMode
    price: float
    stock_status: StockStatus
    notes: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True