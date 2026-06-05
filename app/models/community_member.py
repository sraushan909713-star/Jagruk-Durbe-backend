# app/models/community_member.py
#
# ──────────────────────────────────────────────────────────────────
# Community Members — People who have applied for a Job Alert
# or are availing a Government Scheme in Durbe village.
#
# Purpose: Social awareness — when villagers see their neighbours
# benefiting from schemes or applying for jobs, they get motivated.
#
# Two types of members:
#   1. Gram Seva users  → gram_seva_user_id is filled
#   2. Non-users (elderly etc.) → Admin adds manually, no user_id
#
# One entry belongs to EITHER a job OR a scheme — never both.
# Validation: job_id XOR scheme_id must be present.
#
# Auto-cleanup: Job Alert members are removed after job deadline.
# Scheme members stay permanently.
# ──────────────────────────────────────────────────────────────────

import enum
import uuid
from sqlalchemy import Column, String, Boolean, Date, DateTime, Enum
from sqlalchemy.sql import func
from app.database import Base


class Gender(str, enum.Enum):
    """
    Used to show the correct icon next to each member's entry.
    male   → 👨 icon in Flutter
    female → 👩 icon in Flutter
    """
    male   = "male"
    female = "female"


class CommunityMember(Base):
    __tablename__ = "community_members"

    # — Identity ──────────────────────────────────────────────────
    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    village_id = Column(String, nullable=False, default="1")

    # — Link to Job Alert OR Scheme (one must be set, not both) ───
    job_id    = Column(String, nullable=True)   # FK to job_alerts.id
    scheme_id = Column(String, nullable=True)   # FK to schemes.id

    # — Person details ────────────────────────────────────────────
    name          = Column(String, nullable=False)  # Person's full name
    relative_name = Column(String, nullable=False)  # Pita ka naam / Pati ka naam
    gender        = Column(Enum(Gender), nullable=False)
    since_date    = Column(Date, nullable=False)    # Date applied / availing since

    # — Optional Gram Seva profile link ───────────────────────────
    # If person is on Gram Seva, link their account for profile photo
    gram_seva_user_id = Column(String, nullable=True)
    photo_url         = Column(String, nullable=True)  # Profile photo URL

    # — Admin who added this entry ────────────────────────────────
    added_by_admin_id = Column(String, nullable=False)

    # — Visibility ────────────────────────────────────────────────
    # Soft delete — Admin can remove incorrect entries
    is_active = Column(Boolean, default=True, nullable=False)

    # — Timestamps ────────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    