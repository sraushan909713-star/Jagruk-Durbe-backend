# app/models/vendor_listing.py
# ─────────────────────────────────────────────────────────────
# Defines the "vendor_listings" table — Mandi prices.
# Each row = one vendor's price for one item on either the
# buy side (vendor buys from farmer) or sell side (vendor
# sells to villager). Same vendor can list paddy on buy side
# AND wheat on sell side, but not two buy entries for the
# same item.
# ─────────────────────────────────────────────────────────────

import uuid
import enum
from sqlalchemy import (
    Column, String, Boolean, DateTime, Enum, Text, ForeignKey, Float,
    UniqueConstraint
)
from sqlalchemy.sql import func
from app.database import Base


class TradeMode(str, enum.Enum):
    """
    Which side of the mandi is this price for?
      buy  = vendor BUYS this item from farmers (e.g. paddy)
      sell = vendor SELLS this item to villagers (e.g. rice)
    """
    buy = "buy"
    sell = "sell"


class StockStatus(str, enum.Enum):
    """
    UI labels swap by mode:
      sell mode → "In Stock / Limited / Out of Stock"
      buy mode  → "Khareed rahe hain / Limited / Abhi nahi khareed rahe"
    Same enum value, different display string on Flutter side.
    """
    in_stock     = "in_stock"
    limited      = "limited"
    out_of_stock = "out_of_stock"


class VendorListing(Base):
    __tablename__ = "vendor_listings"

    # — Identity ──────────────────────────────────────────────
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # — Village tag ───────────────────────────────────────────
    village_id = Column(String, nullable=False, default="1")

    # — Vendor ────────────────────────────────────────────────
    vendor_id   = Column(String, nullable=False, index=True)   # FK to users.id
    vendor_name = Column(String, nullable=False)               # Denormalized

    # — Item & unit (FKs to master tables) ────────────────────
    item_id = Column(String, ForeignKey("items.id"), nullable=False, index=True)
    unit_id = Column(String, ForeignKey("units.id"), nullable=False)

    # — Trade side ────────────────────────────────────────────
    mode = Column(Enum(TradeMode), nullable=False, index=True)

    # — Pricing ───────────────────────────────────────────────
    price = Column(Float, nullable=False)

    # — Stock status ──────────────────────────────────────────
    stock_status = Column(
        Enum(StockStatus),
        nullable=False,
        default=StockStatus.in_stock
    )

    # — Extras ────────────────────────────────────────────────
    notes = Column(Text, nullable=True)

    # — Soft delete ───────────────────────────────────────────
    is_active = Column(Boolean, nullable=False, default=True)

    # — Timestamps ────────────────────────────────────────────
    # updated_at auto-updates on PUT — powers freshness colors.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # — Constraints ───────────────────────────────────────────
    # A vendor can't have two active rows for the same item on the same side.
    __table_args__ = (
        UniqueConstraint("vendor_id", "item_id", "mode", name="uq_vendor_item_mode"),
    )