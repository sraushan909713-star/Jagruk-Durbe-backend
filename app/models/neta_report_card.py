# app/models/neta_report_card.py
# ─────────────────────────────────────────────────────────────
# Neta Ka Report Card — Rate Your Representative
#
# Three models:
#   Neta          → a registered leader (Sarpanch, MLA, MP etc.)
#   RatingWindow  → the 6-month cycle window (auto + admin control)
#   NetaRating    → a single verified user's rating in one window
#
# Rules:
#   - Only Durbe Niwasi (verified) users can rate
#   - One rating per user per neta per window — locked after submit
#   - Rating windows auto-open Jan 1 and Jul 1 for 10 days
#   - Super Admin can force-close any window via is_hidden flag
# ─────────────────────────────────────────────────────────────

import uuid
from sqlalchemy import (
    Column, String, Integer,
    Boolean, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


# ─── Neta (Leader) ───────────────────────────────────────────

class Neta(Base):
    __tablename__ = "netas"

    # ── Identity ──────────────────────────────────────────────
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # ── Leader details ────────────────────────────────────────
    name        = Column(String, nullable=False)
    designation = Column(String, nullable=False)   # Sarpanch / Ward Member / MLA / MP / Other
    party       = Column(String, nullable=True)    # Political party name
    photo_url   = Column(String, nullable=True)    # Cloudinary URL

    # ── Visibility ────────────────────────────────────────────
    is_active = Column(Boolean, default=True, nullable=False)

    # ── Timestamps ────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    ratings = relationship("NetaRating", back_populates="neta")


# ─── Rating Window ───────────────────────────────────────────

class RatingWindow(Base):
    __tablename__ = "rating_windows"

    # ── Identity ──────────────────────────────────────────────
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # ── Window schedule ───────────────────────────────────────
    # e.g. label="Jan 2025", opens Jan 1, closes Jan 10
    label      = Column(String, nullable=False)               # "Jan 2025" / "Jul 2025"
    opens_at   = Column(DateTime(timezone=True), nullable=False)
    closes_at  = Column(DateTime(timezone=True), nullable=False)

    # ── Admin override ────────────────────────────────────────
    # Super Admin can set is_hidden=True to force-close a window
    is_hidden  = Column(Boolean, default=False, nullable=False)

    # ── Timestamps ────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ─────────────────────────────────────────
    ratings = relationship("NetaRating", back_populates="window")


# ─── Neta Rating ─────────────────────────────────────────────

class NetaRating(Base):
    __tablename__ = "neta_ratings"

    # ── Identity ──────────────────────────────────────────────
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # ── Foreign keys ──────────────────────────────────────────
    neta_id   = Column(String, ForeignKey("netas.id"),          nullable=False)
    window_id = Column(String, ForeignKey("rating_windows.id"), nullable=False)
    rated_by  = Column(String, ForeignKey("users.id"),          nullable=False)

    # ── Rating ────────────────────────────────────────────────
    stars = Column(Integer, nullable=False)   # 1 to 5

    # ── Visibility ────────────────────────────────────────────
    is_active = Column(Boolean, default=True, nullable=False)

    # ── Timestamps ────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ─────────────────────────────────────────
    neta   = relationship("Neta",         back_populates="ratings")
    window = relationship("RatingWindow", back_populates="ratings")
    rater  = relationship("User",         backref="neta_ratings")

    # ── Constraint: one rating per user per neta per window ───
    __table_args__ = (
        UniqueConstraint("neta_id", "window_id", "rated_by",
                         name="uq_one_rating_per_window"),
    )