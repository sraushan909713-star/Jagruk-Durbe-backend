# app/models/price_history.py
# ─────────────────────────────────────────────────────────────
# Price history — one row per price EVENT (not a daily snapshot).
#
# Written when a vendor:
#   • creates a listing (the first price point)
#   • updates the price on an existing listing
#
# We do NOT snapshot daily. Vendors rarely change prices, so a
# handful of event rows fully describes the trend: the chart
# connects the points, drawing a flat line across the stretches
# where the price held steady and a step where it changed.
#
# This needs no scheduler/cron — nothing to silently break.
# History is honest: only real price events are recorded; flat
# segments are drawn by connecting real points, never faked.
# ─────────────────────────────────────────────────────────────

import uuid
from sqlalchemy import (
    Column, String, Float, DateTime, Enum, ForeignKey, Index
)
from sqlalchemy.sql import func
from app.database import Base
from app.models.vendor_listing import TradeMode


class PriceHistory(Base):
    __tablename__ = "price_history"

    # — Identity ──────────────────────────────────────────────
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # — What this price was for ────────────────────────────────
    # Keyed by item + vendor + mode so a trend can be drawn per
    # vendor, and combined (lowest/highest) across vendors per item.
    item_id   = Column(String, ForeignKey("items.id"), nullable=False, index=True)
    vendor_id = Column(String, nullable=False, index=True)   # users.id
    mode      = Column(Enum(TradeMode), nullable=False, index=True)

    # — The recorded price ────────────────────────────────────
    price = Column(Float, nullable=False)

    # — When this price took effect ───────────────────────────
    recorded_at = Column(DateTime(timezone=True),
                        server_default=func.now(), nullable=False)

    # — Index to make "this item, this side, over time" fast ──
    __table_args__ = (
        Index("ix_price_history_item_mode_time",
              "item_id", "mode", "recorded_at"),
    )