# app/routers/banners.py
# ─────────────────────────────────────────────────────────────
# Home Screen Banners API.
#
# PUBLIC:
#   GET  /banners/        → active, non-expired banners (with contacts)
#
# SUPER ADMIN ONLY:
#   POST   /banners/      → create banner + tag contacts
#   PATCH  /banners/{id}  → edit banner (optionally replace contacts)
#   DELETE /banners/{id}  → soft delete (is_active=False)
#
# Every banner opens an internal detail page in Flutter. The GET
# response carries everything that page needs, including the
# tagged contact users.
# ─────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app.database import get_db
from app.models.banner import Banner, BannerContact
from app.models.user import User
from app.schemas.banner import BannerCreate, BannerUpdate
from app.core.security import decode_access_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/banners", tags=["Banners"])
bearer_scheme = HTTPBearer()


# ─── Helpers ─────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


def require_super_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    role = current_user.role.value if hasattr(current_user.role, "value") \
        else current_user.role
    if role != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="Super Admin access required to manage banners."
        )
    return current_user


def _serialize_banner(banner: Banner) -> dict:
    """
    Builds the full banner response including nested tagged contacts.
    Deleted/inactive tagged users are filtered out so a banner never
    shows "Deleted user" as a contact.
    """
    contacts = []
    for c in banner.contacts:
        u = c.user
        if not u or not u.is_active:
            continue
        contacts.append({
            "user_id":           u.id,
            "full_name":         u.full_name,
            "phone":             u.phone,
            "profile_photo_url": u.profile_photo_url,
            "badge":             u.badge,
            "role":              u.role.value if hasattr(u.role, "value") else u.role,
        })

    return {
        "id":             banner.id,
        "village_id":     banner.village_id,
        "title":          banner.title,
        "description":    banner.description,
        "color_theme":    banner.color_theme,
        "subtitle":       banner.subtitle,
        "icon":           banner.icon,
        "tag":            banner.tag,
        "event_location": banner.event_location,
        "event_date":     banner.event_date,
        "event_time":     banner.event_time,
        "entry_fee":      banner.entry_fee,
        "youtube_link":   banner.youtube_link,
        "external_link":  banner.external_link,
        "image_url":      banner.image_url,
        "display_order":  banner.display_order,
        "valid_until":    banner.valid_until.isoformat() if banner.valid_until else None,
        "is_active":      banner.is_active,
        "created_at":     banner.created_at.isoformat() if banner.created_at else None,
        "contacts":       contacts,
    }


def _attach_contacts(db: Session, banner: Banner, user_ids: List[str]) -> None:
    """
    Validates each user_id exists + is active, then creates BannerContact rows.
    Raises 400 on the first bad id. Caller is responsible for commit.
    Silently skips duplicate user_ids in the same payload.
    """
    seen = set()
    for uid in user_ids:
        if uid in seen:
            continue
        seen.add(uid)
        user = db.query(User).filter(
            User.id == uid, User.is_active == True
        ).first()
        if not user:
            raise HTTPException(
                status_code=400,
                detail=f"Tagged contact not found or inactive: {uid}"
            )
        db.add(BannerContact(banner_id=banner.id, user_id=uid))


# ─── Public ──────────────────────────────────────────────────

@router.get("/")
def get_active_banners(db: Session = Depends(get_db)):
    """
    Returns active, non-expired banners sorted by display_order.
    Flutter calls this on home screen load. No login required.
    """
    now = datetime.utcnow()
    banners = db.query(Banner).filter(
        Banner.is_active == True,
    ).order_by(Banner.display_order.asc()).all()

    active = []
    for b in banners:
        if b.valid_until is None:
            active.append(b)
        else:
            # Compare naive UTC — strip tzinfo for safe comparison
            vu = b.valid_until.replace(tzinfo=None) \
                if b.valid_until.tzinfo else b.valid_until
            if vu > now:
                active.append(b)

    return [_serialize_banner(b) for b in active]


# ─── Super Admin only ────────────────────────────────────────

@router.post("/", status_code=201)
def create_banner(
    data: BannerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Super Admin adds a new banner and tags contact users."""
    banner_fields = data.model_dump(exclude={"contact_user_ids"})
    # color_theme is a Pydantic enum — convert to plain string for DB
    banner_fields["color_theme"] = banner_fields["color_theme"].value \
        if hasattr(banner_fields["color_theme"], "value") \
        else banner_fields["color_theme"]

    banner = Banner(**banner_fields)
    db.add(banner)
    db.flush()  # assigns banner.id before we attach contacts

    _attach_contacts(db, banner, data.contact_user_ids)

    db.commit()
    db.refresh(banner)
    return _serialize_banner(banner)


@router.patch("/{banner_id}")
def update_banner(
    banner_id: str,
    data: BannerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Super Admin edits a banner.
    contact_user_ids replaces the contact set if sent; if omitted,
    contacts are left untouched.
    """
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found.")

    payload = data.model_dump(exclude_unset=True)
    new_contacts = payload.pop("contact_user_ids", None)

    # Coerce color_theme enum → string if present
    if "color_theme" in payload and hasattr(payload["color_theme"], "value"):
        payload["color_theme"] = payload["color_theme"].value

    for field, value in payload.items():
        setattr(banner, field, value)

    # Replace contacts only if caller explicitly sent the field
    if new_contacts is not None:
        db.query(BannerContact).filter(
            BannerContact.banner_id == banner.id
        ).delete()
        db.flush()
        _attach_contacts(db, banner, new_contacts)

    db.commit()
    db.refresh(banner)
    return _serialize_banner(banner)


@router.delete("/{banner_id}", status_code=200)
def delete_banner(
    banner_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Soft-deletes a banner (is_active = False)."""
    banner = db.query(Banner).filter(Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found.")
    banner.is_active = False
    db.commit()
    return {"message": "Banner removed successfully."}