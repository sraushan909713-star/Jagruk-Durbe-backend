# app/models/promise.py
# ─────────────────────────────────────────────────────────────
# Promises — Neta ke Vaade
#
# Two models:
#   Promise         → a promise made by a leader (admin posts)
#   PromiseWitness  → a verified resident who confirms the promise
#
# Rules:
#   - Only admin/super_admin can add, update status, delete
#   - Only Durbe Niwasi (verified) users can witness
#   - One witness tap per user per promise — irreversible
# ─────────────────────────────────────────────────────────────

import uuid
from sqlalchemy import (
    Column, String, Text, Integer,
    Boolean, DateTime, ForeignKey, UniqueConstraint, Date
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


# ─── Promise ─────────────────────────────────────────────────

class Promise(Base):
    __tablename__ = "promises"

    # ── Identity ──────────────────────────────────────────────
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # ── Leader details ────────────────────────────────────────
    leader_name = Column(String, nullable=False)
    leader_role = Column(String, nullable=False)   # mukhiya / vidhayak / mp / sarpanch / other

    # ── Promise details ───────────────────────────────────────
    promise_text      = Column(Text,    nullable=False)
    made_where        = Column(String,  nullable=False)  # rally / village_visit / personal_meeting / other
    made_where_detail = Column(String,  nullable=True)   # e.g. "Durbe main chowk"
    made_on           = Column(Date,    nullable=False)  # date the promise was made
    deadline          = Column(Date,    nullable=True)   # by when it should be fulfilled
    crowd_count       = Column(Integer, nullable=True)   # how many people were present
    youtube_link      = Column(String,  nullable=True)   # ✅ ADD: optional video proof of the promise

    # ── Status ────────────────────────────────────────────────
    # pending → fulfilled / half_delivered / broken
    # Only the poster or super_admin can update this
    status = Column(String, default="pending", nullable=False)

    # ── Audit ─────────────────────────────────────────────────
    created_by  = Column(String, ForeignKey("users.id"), nullable=False)
    village_id  = Column(Integer, nullable=True, default=1)

    # ── Visibility ────────────────────────────────────────────
    is_active = Column(Boolean, default=True, nullable=False)

    # ── Timestamps ────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────
    witnesses = relationship("PromiseWitness", back_populates="promise")
    creator   = relationship("User", backref="promises_created", foreign_keys=[created_by])


# ─── Promise Witness ─────────────────────────────────────────

class PromiseWitness(Base):
    __tablename__ = "promise_witnesses"

    # ── Identity ──────────────────────────────────────────────
    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # ── Foreign keys ──────────────────────────────────────────
    promise_id   = Column(String, ForeignKey("promises.id"), nullable=False)
    user_id      = Column(String, ForeignKey("users.id"),    nullable=False)

    # ── Timestamps ────────────────────────────────────────────
    witnessed_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ─────────────────────────────────────────
    promise  = relationship("Promise", back_populates="witnesses")
    user     = relationship("User", backref="witnessed_promises")

    # ── One witness tap per user per promise ──────────────────
    __table_args__ = (
        UniqueConstraint("promise_id", "user_id",
                         name="uq_one_witness_per_promise"),
    )