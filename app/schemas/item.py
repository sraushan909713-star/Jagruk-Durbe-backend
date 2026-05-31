# app/schemas/item.py
# ─────────────────────────────────────────────────────────────
# Pydantic schemas for the items master catalog.
# ─────────────────────────────────────────────────────────────

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# — REQUEST SCHEMAS ───────────────────────────────────────────

class ItemCreate(BaseModel):
    """
    Vendor or admin creates a new item.
    is_custom is set automatically: True if requester is vendor, False if admin.
    created_by_vendor_id is taken from JWT — not sent manually.
    """
    name: str
    name_hindi: Optional[str] = None
    default_unit_id: Optional[str] = None
    category: Optional[str] = None
    display_order: int = 999


class ItemUpdate(BaseModel):
    """
    Admin only. Fixes typos, reorders the curated list, updates default unit.
    """
    name: Optional[str] = None
    name_hindi: Optional[str] = None
    default_unit_id: Optional[str] = None
    category: Optional[str] = None
    display_order: Optional[int] = None


# — RESPONSE SCHEMA ───────────────────────────────────────────

class ItemResponse(BaseModel):
    id: str
    name: str
    name_hindi: Optional[str]
    default_unit_id: Optional[str]
    category: Optional[str]
    display_order: int
    is_custom: bool
    created_by_vendor_id: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True