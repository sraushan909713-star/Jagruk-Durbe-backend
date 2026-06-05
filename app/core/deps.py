# app/core/deps.py
# ─────────────────────────────────────────────────────────────
# Centralized authentication and authorization dependencies.
#
# All routers MUST import auth helpers from this module — never define
# their own copies. Single source of truth ensures critical invariants
# (e.g. the `is_active` check that blocks deactivated users from
# continuing to use old JWTs) cannot be accidentally omitted by a
# router author.
#
# Helpers:
#   get_current_user      — any authenticated, ACTIVE user
#   require_verified      — verified Durbe Niwasi OR admin/super_admin
#   require_vendor_or_admin — vendor OR admin/super_admin
#   require_admin         — admin OR super_admin
#   require_super_admin   — super_admin only
# ─────────────────────────────────────────────────────────────

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer()


# ─── Authentication ──────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode JWT, fetch user, verify account is still active.

    Returns the authenticated User. Raises 401 on any of:
      - Token missing / invalid / expired
      - User row not found
      - User has been deactivated (soft-deleted or admin-disabled)

    The `is_active` check is critical: without it, /delete-account
    would not actually revoke session access — JWTs issued before
    deactivation would keep working until they naturally expire.
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or deactivated.")
    return user


# ─── Authorization ──────────────────────────────────────────

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Admin or Super Admin only."""
    if current_user.role not in (UserRole.admin, UserRole.super_admin):
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user


def require_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Super Admin only."""
    if current_user.role != UserRole.super_admin:
        raise HTTPException(status_code=403, detail="Super Admin access required.")
    return current_user


def require_verified(current_user: User = Depends(get_current_user)) -> User:
    """Verified Durbe Niwasi residents, or any admin/super_admin.

    Use on actions that should require accountable identity in the village
    (posting complaints, signing petitions, rating leaders, etc).
    """
    if current_user.role in (UserRole.admin, UserRole.super_admin):
        return current_user
    if not current_user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Only verified Durbe Niwasi residents can perform this action.",
        )
    return current_user


def require_vendor_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Vendor, Admin, or Super Admin. Use on routes where vendors manage
    their own catalog (items, units, listings) but admins also have power."""
    if current_user.role not in (UserRole.vendor, UserRole.admin, UserRole.super_admin):
        raise HTTPException(
            status_code=403,
            detail="Vendor or Admin access required.",
        )
    return current_user
