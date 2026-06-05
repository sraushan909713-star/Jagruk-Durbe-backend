# app/schemas/vikas_prastav.py
# ─────────────────────────────────────────────
# Pydantic schemas for Vikas Prastav (Development Proposals).
# ─────────────────────────────────────────────

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.vikas_prastav import ProposalCategory


# ── REQUEST SCHEMAS ────────────────────────────────────────────

class VikasPrastavCreate(BaseModel):
    """
    Used when a logged-in user submits a new development proposal.
    """
    title: str
    description: str
    location: str
    category: ProposalCategory
    photo_url_1: str
    photo_url_2: Optional[str] = None
    photo_url_3: Optional[str] = None
    photo_url_4: Optional[str] = None
    estimated_cost: Optional[str] = None   # e.g. "₹2-3 lakh" — optional
    funding_source: Optional[str] = None   # e.g. "MGNREGA" — optional


# ── RESPONSE SCHEMAS ───────────────────────────────────────────

class VikasPrastavListResponse(BaseModel):
    """
    Lightweight summary for the proposals list screen.
    """
    id: str
    title: str
    location: str
    category: ProposalCategory
    photo_url_1: str
    upvote_count: int
    posted_by: str
    poster_name:  Optional[str] = None
    poster_photo: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class VikasPrastavResponse(BaseModel):
    """
    Full proposal detail — shown when user taps on a proposal.
    """
    id: str
    title: str
    description: str
    location: str
    category: ProposalCategory
    estimated_cost: Optional[str] = None
    funding_source: Optional[str] = None
    photo_url_1: str
    photo_url_2: Optional[str] = None
    photo_url_3: Optional[str] = None
    photo_url_4: Optional[str] = None
    upvote_count: int
    posted_by: str
    poster_name:  Optional[str] = None
    poster_photo: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UpvoteResponse(BaseModel):
    """Returned after a successful upvote."""
    message: str
    upvote_count: int