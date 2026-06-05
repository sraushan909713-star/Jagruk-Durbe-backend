# app/schemas/gram_awaaz.py
# ─────────────────────────────────────────────
# Pydantic schemas for Gram Awaaz (Village Voice) feature.
# ─────────────────────────────────────────────

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.gram_awaaz import Department


# ── REQUEST SCHEMAS ────────────────────────────────────────────

class GramAwaazCreate(BaseModel):
    """
    Used when a logged-in user creates a new complaint post.
    All fields are required — enforcing our evidence-over-emotion principle.
    """
    title: str                      # Short headline
    description: str                # Full story
    location: str                   # Area within Durbe
    affected_count: int             # How many people affected
    department: Department          # Which dept is responsible
    demand: str                     # Specific ask
    photo_url_1: str              # Mandatory evidence photo
    photo_url_2: Optional[str] = None
    photo_url_3: Optional[str] = None
    photo_url_4: Optional[str] = None


# ── RESPONSE SCHEMAS ───────────────────────────────────────────

class PosterInfo(BaseModel):
    """Basic info about the person who posted the complaint."""
    id: str
    name: str

    class Config:
        from_attributes = True


class GramAwaazListResponse(BaseModel):
    """
    Lightweight summary for the list screen.
    Shows enough to make the post feel impactful — photo, title, upvotes.
    """
    id: str
    title: str
    location: str
    affected_count: int
    department: Department
    photo_url_1: str
    upvote_count: int
    posted_by: str  
    poster_name:  Optional[str] = None
    poster_photo: Optional[str] = None               
    created_at: datetime

    class Config:
        from_attributes = True


class GramAwaazResponse(BaseModel):
    """
    Full post detail — shown when user taps on a complaint.
    """
    id: str
    title: str
    description: str
    location: str
    affected_count: int
    department: Department
    demand: str
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