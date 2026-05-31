# app/schemas/unit.py
# ─────────────────────────────────────────────────────────────
# Pydantic schemas for the units master table.
# ─────────────────────────────────────────────────────────────

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UnitCreate(BaseModel):
    name: str
    name_hindi: Optional[str] = None


class UnitUpdate(BaseModel):
    name: Optional[str] = None
    name_hindi: Optional[str] = None


class UnitResponse(BaseModel):
    id: str
    name: str
    name_hindi: Optional[str]
    is_custom: bool
    created_by_vendor_id: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True