# app/schemas/banner.py
# ─────────────────────────────────────────────────────────────
# Pydantic schemas for Home Screen Banners.
#
# Banners always open an internal detail page in Flutter. The
# schemas describe what Super Admin sends when creating or
# editing a banner, and what Flutter receives back (including
# the nested tagged contacts).
# ─────────────────────────────────────────────────────────────

import enum
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class BannerColorTheme(str, enum.Enum):
    """
    Curated gradient themes — kept in sync with VALID_COLOR_THEMES
    in app/models/banner.py and the gradient map on the Flutter side.
    """
    indigo_night  = "indigo_night"
    sunset        = "sunset"
    festival      = "festival"
    paddy_field   = "paddy_field"
    monsoon       = "monsoon"
    rosewood      = "rosewood"
    slate         = "slate"
    earthen       = "earthen"
    emergency     = "emergency"
    sunrise       = "sunrise"
    celebration   = "celebration"


# ── REQUEST SCHEMAS (data coming IN from Super Admin) ─────────

class BannerCreate(BaseModel):
    """
    Super Admin creates a new banner.
    title + description + color_theme are mandatory.
    contact_user_ids: list of existing user IDs to tag as contacts.
    """
    title:        str
    description:  str
    color_theme:  BannerColorTheme

    subtitle:     Optional[str] = None
    icon:         Optional[str] = None        # emoji
    tag:          Optional[str] = None        # free-text label

    event_location: Optional[str] = None
    event_date:     Optional[str] = None
    event_time:     Optional[str] = None
    entry_fee:      Optional[str] = None

    youtube_link:  Optional[str] = None
    external_link: Optional[str] = None
    image_url:     Optional[str] = None        # V2 — unused for now

    display_order: int                = 0
    valid_until:   Optional[datetime] = None
    village_id:    str                = "1"

    contact_user_ids: List[str] = []           # users to tag as contacts


class BannerUpdate(BaseModel):
    """
    Super Admin edits a banner — all fields optional.
    If contact_user_ids is sent, it REPLACES the existing contact set.
    If omitted entirely, contacts stay untouched.
    """
    title:        Optional[str] = None
    description:  Optional[str] = None
    color_theme:  Optional[BannerColorTheme] = None

    subtitle:     Optional[str] = None
    icon:         Optional[str] = None
    tag:          Optional[str] = None

    event_location: Optional[str] = None
    event_date:     Optional[str] = None
    event_time:     Optional[str] = None
    entry_fee:      Optional[str] = None

    youtube_link:  Optional[str] = None
    external_link: Optional[str] = None
    image_url:     Optional[str] = None

    display_order: Optional[int]      = None
    valid_until:   Optional[datetime] = None
    is_active:     Optional[bool]     = None

    contact_user_ids: Optional[List[str]] = None   # None = leave untouched


# ── RESPONSE SHAPES (documentation reference) ─────────────────
# NOTE: the router builds responses with an explicit serializer
# (_serialize_banner) and returns plain dicts, because the nested
# contacts come from a join table and don't map cleanly through
# Pydantic's from_attributes. These classes document the shape.

class BannerContactResponse(BaseModel):
    user_id:           str
    full_name:         str
    phone:             str
    profile_photo_url: Optional[str] = None
    badge:             str
    role:              str


class BannerResponse(BaseModel):
    id:           str
    village_id:   str
    title:        str
    description:  str
    color_theme:  str
    subtitle:     Optional[str] = None
    icon:         Optional[str] = None
    tag:          Optional[str] = None

    event_location: Optional[str] = None
    event_date:     Optional[str] = None
    event_time:     Optional[str] = None
    entry_fee:      Optional[str] = None

    youtube_link:  Optional[str] = None
    external_link: Optional[str] = None
    image_url:     Optional[str] = None

    display_order: int
    valid_until:   Optional[str] = None
    is_active:     bool
    created_at:    Optional[str] = None

    contacts:      List[BannerContactResponse] = []