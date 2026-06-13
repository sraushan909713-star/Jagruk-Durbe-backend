# app/schemas/promise.py
# ─────────────────────────────────────────────────────────────
# Pydantic schemas for Promises (Neta ke Vaade) feature.
# ─────────────────────────────────────────────────────────────

from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime, date


# ─── Promise Schemas ─────────────────────────────────────────

class PromiseCreate(BaseModel):
    """Admin creates a new promise entry."""
    leader_name:       str
    leader_role:       str              # mukhiya / vidhayak / mp / sarpanch / other
    promise_text:      str
    made_where:        str              # rally / village_visit / personal_meeting / other
    made_where_detail: Optional[str] = None
    made_on:           date
    deadline:          Optional[date] = None
    crowd_count:       Optional[int]  = None
    youtube_link:      Optional[str]  = None   # ✅ ADD

    @field_validator("leader_role")
    @classmethod
    def validate_leader_role(cls, v):
        allowed = {"mukhiya", "vidhayak", "mp", "sarpanch", "other"}
        if v.lower() not in allowed:
            raise ValueError(f"leader_role must be one of: {allowed}")
        return v.lower()

    @field_validator("made_where")
    @classmethod
    def validate_made_where(cls, v):
        allowed = {"rally", "village_visit", "personal_meeting", "other"}
        if v.lower() not in allowed:
            raise ValueError(f"made_where must be one of: {allowed}")
        return v.lower()


class PromiseStatusUpdate(BaseModel):
    """Poster or super_admin updates promise status."""
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        allowed = {"pending", "fulfilled", "half_delivered", "broken"}
        if v.lower() not in allowed:
            raise ValueError(f"status must be one of: {allowed}")
        return v.lower()


class PromiseResponse(BaseModel):
    """Full promise detail — used in list and detail screens."""
    id:                str
    leader_name:       str
    leader_role:       str
    promise_text:      str
    made_where:        str
    made_where_detail: Optional[str]  = None
    made_on:           date
    deadline:          Optional[date] = None
    crowd_count:       Optional[int]  = None
    youtube_link:      Optional[str]  = None   # ✅ ADD
    status:            str
    created_by:        str
    witness_count:     int  = 0        # computed
    has_witnessed:     bool = False    # computed — for logged-in user
    is_active:         bool
    created_at:        datetime

    class Config:
        from_attributes = True


# ─── Witness Schemas ─────────────────────────────────────────

class WitnessResponse(BaseModel):
    """A single witness entry — shown in the witness list."""
    id:           str
    user_id:      str
    full_name:    str             # from User table
    photo_url:    Optional[str] = None
    witnessed_at: datetime

    class Config:
        from_attributes = True