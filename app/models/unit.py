# app/models/unit.py
# ─────────────────────────────────────────────────────────────
# Defines the "units" master table for Mandi feature.
# Units are how prices are measured (per kg, per quintal, etc).
# Pre-seeded with common units; vendors can add custom ones
# (e.g. local measurements like "bori") — go live immediately.
# Admin can soft-delete.
# ─────────────────────────────────────────────────────────────

import uuid
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class Unit(Base):
    __tablename__ = "units"

    # — Identity ──────────────────────────────────────────────
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # — Names ─────────────────────────────────────────────────
    name = Column(String, nullable=False, unique=True, index=True)   # "kg"
    name_hindi = Column(String, nullable=True)                       # "किलो"

    # — Custom-unit provenance ────────────────────────────────
    is_custom = Column(Boolean, nullable=False, default=False)
    created_by_vendor_id = Column(String, nullable=True)

    # — Soft delete ───────────────────────────────────────────
    is_active = Column(Boolean, nullable=False, default=True)

    # — Timestamps ────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())