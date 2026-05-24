# app/models/banner.py
# ─────────────────────────────────────────────────────────────
# Home Screen Banners — civic entry points.
#
# DESIGN PHILOSOPHY:
#   Every banner ALWAYS opens an internal detail page when tapped.
#   No banner ever redirects to a screen or jumps to a browser.
#   The detail page itself may then contain an embedded YouTube
#   video, an external link button, and tagged contact users —
#   but those are CONTENTS of the page, not destinations.
#
#   The carousel keeps the old visual model — emoji, two-color
#   gradient, title, subtitle, tag badge — but the gradient now
#   comes from a curated color_theme name instead of freeform hex
#   pairs, so it always looks polished.
#
#   tag stays free text so banner "types" (Voting Drive, Health
#   Camp, Cricket Cup, anything new) are unbounded.
#
#   valid_until auto-hides the banner after an event passes.
#   image_url is reserved for a future V2 Cloudinary upload feature.
#
#   Managed by Super Admin only.
# ─────────────────────────────────────────────────────────────

import uuid
from sqlalchemy import (Column, String, Text, Boolean, DateTime,
                        Integer, ForeignKey)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


# Valid color_theme values (kept in sync with Flutter gradient map).
# Stored as plain String column for easy future extensibility —
# adding a new theme just means updating this tuple, the Pydantic
# validator, and the Flutter gradient map. No DB migration needed.
VALID_COLOR_THEMES = (
    "indigo_night",
    "sunset",
    "festival",
    "paddy_field",
    "monsoon",
    "rosewood",
    "slate",
    "earthen",
    "emergency",
    "sunrise",
    "celebration",
)


class Banner(Base):
    __tablename__ = "banners"

    # ── Identity ──────────────────────────────────────────────
    id         = Column(String, primary_key=True,
                        default=lambda: str(uuid.uuid4()))
    village_id = Column(String, nullable=False, default="1")

    # ── Carousel visuals (mirror old design, except color_theme) ──
    title       = Column(String, nullable=False)
    subtitle    = Column(String, nullable=True)
    icon        = Column(String, nullable=True)   # emoji
    tag         = Column(String, nullable=True)   # free-text label
    color_theme = Column(String, nullable=False,
                         default="indigo_night")  # one of VALID_COLOR_THEMES

    # ── Detail page content (mandatory description + optional rest) ──
    description    = Column(Text,   nullable=False)
    event_location = Column(String, nullable=True)
    event_date     = Column(String, nullable=True)
    event_time     = Column(String, nullable=True)
    entry_fee      = Column(String, nullable=True)
    youtube_link   = Column(String, nullable=True)   # embedded on detail page
    external_link  = Column(String, nullable=True)   # opens browser

    # ── Image — V2 feature, column ready but unused in V1 ─────
    image_url = Column(String, nullable=True)

    # ── Display + lifecycle ───────────────────────────────────
    display_order = Column(Integer, default=0, nullable=False)
    valid_until   = Column(DateTime(timezone=True), nullable=True)
    is_active     = Column(Boolean, default=True, nullable=False)

    # ── Timestamps ────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # ── Tagged contacts (many-to-many via banner_contacts) ────
    contacts = relationship(
        "BannerContact",
        back_populates="banner",
        cascade="all, delete-orphan",
    )


class BannerContact(Base):
    """
    Join table — links a banner to one or more real app users
    who appear on the detail page as "contact this person for more info".
    """
    __tablename__ = "banner_contacts"

    id        = Column(String, primary_key=True,
                       default=lambda: str(uuid.uuid4()))
    banner_id = Column(String, ForeignKey("banners.id"), nullable=False)
    user_id   = Column(String, ForeignKey("users.id"),   nullable=False)

    banner = relationship("Banner", back_populates="contacts")
    user   = relationship("User")