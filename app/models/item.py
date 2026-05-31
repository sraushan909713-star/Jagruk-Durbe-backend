# app/models/item.py
# ─────────────────────────────────────────────────────────────
# Defines the "items" master catalog table for Mandi feature.
# Items are the products vendors trade (Chawal, Sarso Tel, etc).
# Pre-seeded by admin; vendors can also add custom items via
# the "Add new item" flow — those go live immediately, no
# moderation. Admin can soft-delete any item.
# ─────────────────────────────────────────────────────────────

import uuid
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Item(Base):
    __tablename__ = "items"

    # — Identity ──────────────────────────────────────────────
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # — Names ─────────────────────────────────────────────────
    # name is English/transliterated ("Chawal"), name_hindi is Devanagari ("चावल")
    name = Column(String, nullable=False, index=True)
    name_hindi = Column(String, nullable=True)

    # — Default unit ──────────────────────────────────────────
    # When a vendor picks this item to list, unit auto-fills with this default.
    # Vendor can override per listing.
    default_unit_id = Column(String, ForeignKey("units.id"), nullable=True)

    # — Optional category ─────────────────────────────────────
    # Not surfaced in V1 UX. Reserved for future filtering
    # (e.g. "grain", "oil", "pulse", "feed", "vegetable").
    category = Column(String, nullable=True)

    # — Curated order ─────────────────────────────────────────
    # Powers the curated home-screen item order.
    # Admin updates this to move items up/down.
    # Lower numbers appear first (1 = top).
    display_order = Column(Integer, nullable=False, default=999)

    # — Custom-item provenance ────────────────────────────────
    # True if added by a vendor via "Add new item" flow.
    # False for admin-seeded master items.
    is_custom = Column(Boolean, nullable=False, default=False)

    # Nullable: null for pre-seeded items, vendor's user.id for custom ones.
    created_by_vendor_id = Column(String, nullable=True)

    # — Soft delete ───────────────────────────────────────────
    is_active = Column(Boolean, nullable=False, default=True)

    # — Timestamps ────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())