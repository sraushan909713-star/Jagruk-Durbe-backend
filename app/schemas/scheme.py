# app/schemas/scheme.py
# ─────────────────────────────────────────────
# Pydantic schemas for the Government Schemes feature.
# These define what data comes IN (requests) and goes OUT (responses).
# Think of schemas as the "contract" between the API and the Flutter app.
# ─────────────────────────────────────────────

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.scheme import SchemeCategory


# ── REQUEST SCHEMAS (data coming IN from Admin) ────────────────────────────

class SchemeCreate(BaseModel):
    """
    Used when Admin creates a new scheme via POST /schemes.
    All fields except optional ones are required.
    """
    name: str
    description: str
    eligibility: str
    how_to_apply: str
    documents_required: str        # ✅ ADD — mandatory
    category: SchemeCategory
    official_link: Optional[str] = None      # Optional — not all schemes have a website
    youtube_link: Optional[str] = None        # ✅ ADD
    additional_info: Optional[str] = None    # Optional — for any extra details


class SchemeUpdate(BaseModel):
    """
    Used when Admin edits a scheme via PUT /schemes/{id}.
    ALL fields are optional — admin only sends what they want to change.
    For example, to only update the description, just send { "description": "..." }
    """
    name: Optional[str] = None
    description: Optional[str] = None
    eligibility: Optional[str] = None
    how_to_apply: Optional[str] = None
    documents_required: Optional[str] = None        # ✅ ADD
    category: Optional[SchemeCategory] = None
    official_link: Optional[str] = None
    youtube_link: Optional[str] = None        # ✅ ADD
    additional_info: Optional[str] = None
    is_active: Optional[bool] = None         # Admin can hide/show a scheme


# ── RESPONSE SCHEMAS (data going OUT to Flutter app) ──────────────────────

class SchemeResponse(BaseModel):
    """
    Returned when viewing a single scheme or a list of schemes.
    This is the full detail view.
    """
    id: str
    name: str
    description: str
    eligibility: str
    how_to_apply: str
    documents_required: str        # ✅ ADD
    category: SchemeCategory
    official_link: Optional[str] = None
    youtube_link: Optional[str] = None        # ✅ ADD
    additional_info: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True      # Allows SQLAlchemy model → Pydantic conversion


class SchemeListResponse(BaseModel):
    """
    Returned by GET /schemes — a summary view for the list screen.
    Excludes heavy fields like how_to_apply to keep the list response light.
    Flutter will fetch the full detail only when user taps on a scheme.
    """
    id: str
    name: str
    description: str
    category: SchemeCategory
    is_active: bool
    youtube_link: Optional[str] = None        # ✅ ADD

    class Config:
        from_attributes = True