# app/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from app.database import get_db
from app.core.otp import create_otp, verify_otp
from app.core.security import hash_password, create_access_token, verify_password, decode_access_token
from app.models.otp import OTPPurpose
from app.models.user import User, UserRole
from app.schemas.auth import SendOTPRequest, RegisterRequest, TokenResponse, LoginRequest, ResetPasswordRequest
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from app.core.limiter import limiter
from fastapi import Request

router = APIRouter(prefix="/auth", tags=["Authentication"])
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
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or deactivated.")
    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user

def require_super_admin(current_user: User = Depends(get_current_user)) -> User:  # ✅ NEW
    if current_user.role != UserRole.super_admin:
        raise HTTPException(status_code=403, detail="Super Admin access required.")
    return current_user


# ─── Request schemas ──────────────────────────────────────────

class ClaimResidencyRequest(BaseModel):
    profile_photo_url: str   # Cloudinary URL — mandatory for claim

class UpdatePhotoRequest(BaseModel):
    profile_photo_url: str   # Called after Cloudinary upload

class PromoteVendorRequest(BaseModel):
    phone:     str
    shop_name: str

class ChangeRoleRequest(BaseModel):
    role: str

class RequestAccountDeletionRequest(BaseModel):                # ✅ NEW
    password: str

class DeleteAccountRequest(BaseModel):                          # ✅ NEW
    password: str
    otp_code: str


# ─── Existing endpoints ───────────────────────────────────────

@router.post("/send-otp")
@limiter.limit("3/5minute")
def send_otp(request: Request, body: SendOTPRequest, db: Session = Depends(get_db)):
    """Send OTP to phone. Returns code in response (dev only)."""
    purpose = OTPPurpose(body.purpose)
    code = create_otp(db, phone=body.phone, purpose=purpose)
    return {
        "message": f"OTP sent to {body.phone}",
        "otp": code  # ⚠️ REMOVE IN PRODUCTION
    }


@router.post("/register", response_model=TokenResponse)
@limiter.limit("3/10minute")
def register(request: Request, body: RegisterRequest, db: Session = Depends(get_db)):
    """Verify OTP + create user account + return JWT token."""
    otp_valid = verify_otp(
        db, phone=body.phone, code=body.otp_code,
        purpose=OTPPurpose.registration
    )
    if not otp_valid:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # ✅ Phone uniqueness:
    # On account deletion we rename the deleted user's phone to
    # "deleted_<user.id>" — so the original phone is free to reuse here.
    # No filter on is_active needed; the DB already won't match deleted phones.
    existing = db.query(User).filter(User.phone == body.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone already registered")

    new_user = User(
        phone=body.phone,
        full_name=body.name,
        display_name=body.name,
        password_hash=hash_password(body.password),
        role=UserRole.user,
        village_id=1,
        is_durbe_resident=False,
        is_verified=False,
        is_active=True,
        badge="none",           # default is "none" — user must claim residency
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token(data={
        "sub": str(new_user.id),
        "role": new_user.role,
        "badge": new_user.badge,
    })
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    """Login with phone + password."""
    user = db.query(User).filter(User.phone == body.phone).first()
    if not user:
        raise HTTPException(status_code=400,
            detail="No account found with this phone number")

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect password")

    if not user.is_active:
        raise HTTPException(status_code=400,
            detail="Your account has been deactivated. Contact admin.")

    token = create_access_token(data={
        "sub": str(user.id),
        "role": user.role.value,
        "badge": user.badge,
    })

    # Return full user info so Flutter can save to SharedPreferences
    return {
        "access_token": token,
        "token_type": "bearer",
        "id": str(user.id),
        "role": user.role.value,
        "badge": user.badge,
        "is_verified": user.is_verified,
        "full_name": user.full_name,
        "phone": user.phone,
        "profile_photo_url": user.profile_photo_url,
    }


@router.post("/reset-password", response_model=TokenResponse)
@limiter.limit("5/minute")
def reset_password(request: Request, body: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset forgotten password using OTP verification."""
    user = db.query(User).filter(User.phone == body.phone).first()
    if not user:
        raise HTTPException(status_code=400,
            detail="No account found with this phone number")

    otp_valid = verify_otp(
        db, phone=body.phone, code=body.otp_code,
        purpose=OTPPurpose.reset_password
    )
    if not otp_valid:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    user.password_hash = hash_password(body.new_password)
    db.commit()

    token = create_access_token(data={
        "sub": str(user.id),
        "role": user.role.value,
        "badge": user.badge,
    })
    return {"access_token": token, "token_type": "bearer"}


# ─── Profile & residency endpoints ────────────────────────────

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """
    Returns full profile of the logged-in user.
    Flutter calls this on Profile screen load.
    """
    return {
        "id":                     current_user.id,
        "full_name":              current_user.full_name,
        "display_name":           current_user.display_name,
        "phone":                  current_user.phone,
        "role":                   current_user.role.value,
        "badge":                  current_user.badge,
        "is_verified":            current_user.is_verified,
        "is_durbe_resident":      current_user.is_durbe_resident,
        "profile_photo_url":      current_user.profile_photo_url,
        "verification_photo_url": current_user.verification_photo_url,        # ✅ NEW
        "verified_by":            current_user.verified_by,
        "verified_at":            current_user.verified_at.isoformat()
                                  if current_user.verified_at else None,
        "created_at":             current_user.created_at.isoformat()
                                  if current_user.created_at else None,
        "village_id":             current_user.village_id,
    }


@router.post("/claim-residency")
def claim_residency(
    data: ClaimResidencyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    User claims Durbe residency and uploads a profile photo.
    Sets badge = 'pending'. Admin will then approve or reject.
    Profile photo is mandatory — admin uses it to identify the person.
    """
    if current_user.badge == "durbe_niwasi":
        raise HTTPException(status_code=400,
            detail="You are already a verified Durbe Niwasi.")

    if current_user.badge == "pending":
        raise HTTPException(status_code=400,
            detail="Your verification is already pending. Please wait for admin approval.")

    if not data.profile_photo_url:
        raise HTTPException(status_code=400,
            detail="Profile photo is required to claim residency.")

    current_user.badge              = "pending"
    current_user.is_durbe_resident  = True
    current_user.profile_photo_url  = data.profile_photo_url
    db.commit()

    return {"message": "Residency claim submitted. Admin will review and approve soon."}


@router.get("/pending-verifications")
def get_pending_verifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Admin sees list of all users with badge = 'pending'.
    Shows name, phone, profile photo for identification.
    """
    pending = db.query(User).filter(
        User.badge     == "pending",
        User.is_active == True
    ).order_by(User.created_at.desc()).all()

    return [
        {
            "id":                u.id,
            "full_name":         u.full_name,
            "phone":             u.phone,
            "profile_photo_url": u.profile_photo_url,
            "created_at":        u.created_at.isoformat() if u.created_at else None,
        }
        for u in pending
    ]


@router.post("/verify/{user_id}")
def verify_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Admin approves a pending residency claim.
    Records who approved and when — full audit trail.
    ✅ Now ALSO copies profile_photo_url → verification_photo_url
       so we have a permanent audit photo even if the user
       later changes their public DP.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.badge != "pending":
        raise HTTPException(status_code=400,
            detail="User does not have a pending verification request.")

    user.badge                  = "durbe_niwasi"
    user.is_verified            = True
    user.is_durbe_resident      = True
    user.verification_photo_url = user.profile_photo_url    # ✅ NEW — lock in the audit photo
    user.verified_by            = current_user.id           # audit: who approved
    user.verified_at            = datetime.utcnow()         # audit: when approved
    db.commit()

    return {
        "message": f"{user.full_name} has been verified as Durbe Niwasi.",
        "verified_by": current_user.full_name,
        "verified_at": user.verified_at.isoformat(),
    }


@router.post("/revoke/{user_id}")
def revoke_verification(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Admin removes Durbe Niwasi badge from a user.
    Used when a badge was wrongly given or abused.

    ✅ Guards:
      - Cannot revoke your own badge (admin self-protection)
      - Cannot revoke a super_admin's badge
      - Also clears verification_photo_url (the audit photo)
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # ✅ Self-protection — admin can't accidentally revoke their own badge
    if user.id == current_user.id:
        raise HTTPException(status_code=400,
            detail="You cannot revoke your own badge.")

    # ✅ Super-admin protection — keeps the trust chain intact
    if user.role == UserRole.super_admin:
        raise HTTPException(status_code=403,
            detail="Cannot revoke a Super Admin's badge.")

    if user.badge not in ("durbe_niwasi", "pending"):
        raise HTTPException(status_code=400,
            detail="User does not have a badge to revoke.")

    user.badge                  = "none"
    user.is_verified            = False
    user.is_durbe_resident      = False
    user.verification_photo_url = None                  # ✅ clear audit photo
    user.verified_by            = None
    user.verified_at            = None
    db.commit()

    return {"message": f"{user.full_name}'s verification has been revoked."}


@router.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Admin gets list of all active registered users.
    Returns name, role, badge, photo only — NO phone (privacy).
    ✅ Now ALSO returns verification_photo_url so admin can
       inspect the original audit photo in the member detail screen.
    """
    users = db.query(User).filter(
        User.is_active == True
    ).order_by(User.created_at.desc()).all()

    return [
        {
            "id":                     u.id,
            "full_name":              u.full_name,
            "role":                   u.role.value,
            "badge":                  u.badge,
            "profile_photo_url":      u.profile_photo_url,
            "verification_photo_url": u.verification_photo_url,    # ✅ NEW
            "verified_at":            u.verified_at.isoformat() if u.verified_at else None,
            "created_at":             u.created_at.isoformat()    if u.created_at    else None,
        }
        for u in users
    ]


@router.patch("/update-photo")
def update_profile_photo(
    data: UpdatePhotoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update profile photo URL after Cloudinary upload.

    ✅ AUTO-REVOKE LOGIC:
       If the user is currently verified (badge = 'durbe_niwasi') and
       they change their photo, their badge is automatically revoked.
       They will need to re-claim residency and get re-approved.

       This protects the trust model — the badge means "the admin
       saw this exact face." If the face changes, the badge dies.

       Frontend MUST show a warning dialog before calling this
       endpoint for a verified user.

       Behavior by current badge state:
         - 'none'         → free change, badge stays 'none'
         - 'pending'      → free change, badge stays 'pending'
                            (new photo replaces the pending photo;
                             admin will judge whichever is current)
         - 'durbe_niwasi' → AUTO-REVOKE: badge → 'none', audit photo cleared
    """
    badge_was_revoked = False

    if current_user.badge == "durbe_niwasi":
        # Auto-revoke — the verified face is no longer the public face.
        current_user.badge                  = "none"
        current_user.is_verified            = False
        current_user.is_durbe_resident      = False
        current_user.verification_photo_url = None
        current_user.verified_by            = None
        current_user.verified_at            = None
        badge_was_revoked = True

    current_user.profile_photo_url = data.profile_photo_url
    db.commit()

    if badge_was_revoked:
        return {
            "message":          "Photo updated. Your Durbe Niwasi badge has been revoked because you changed your DP. You may re-claim residency from your profile.",
            "badge_revoked":    True,
            "new_badge":        "none",
        }

    return {
        "message":       "Profile photo updated successfully.",
        "badge_revoked": False,
        "new_badge":     current_user.badge,
    }


# ─── Account deletion (password + OTP, with super-admin self-lock) ────

@router.post("/request-account-deletion")                                # ✅ NEW
def request_account_deletion(
    data: RequestAccountDeletionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Step 1 of account deletion: verify password, send OTP.

    The user must enter their password correctly here. If valid,
    we send an OTP to their phone. They must then call
    /delete-account with both password AND otp_code to finalize.

    Super Admin cannot delete their own account (self-lock).
    """
    # ✅ Super-admin self-lock
    if current_user.role == UserRole.super_admin:
        raise HTTPException(status_code=403,
            detail="Super Admin account cannot be deleted. Demote yourself first or contact another super admin.")

    if not verify_password(data.password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect password.")

    code = create_otp(db, phone=current_user.phone, purpose=OTPPurpose.account_deletion)

    return {
        "message": "OTP sent. Enter it along with your password to confirm deletion.",
        "otp":     code,   # ⚠️ REMOVE IN PRODUCTION
    }


@router.post("/delete-account")                                          # ✅ NEW (replaces DELETE /me)
def delete_account(
    data: DeleteAccountRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Step 2 of account deletion: verify password + OTP, then soft-delete.

    On success:
      - is_active           → False  (blocks all future logins)
      - full_name           → "Deleted user"   (so existing posts show this)
      - display_name        → "Deleted user"
      - phone               → "deleted_<user.id>"   (frees the real phone for re-registration)
      - profile_photo_url   → None
      - verification_photo_url → None
      - badge               → "none"  (also clears verified_by, verified_at, is_verified, is_durbe_resident)
      - deleted_at          → now()   (audit timestamp)

    Posts, votes, likes, ratings, and comments by this user are PRESERVED.
    They will display under "Deleted user" with a generic avatar.

    Super Admin cannot delete their own account (self-lock).
    """
    # ✅ Super-admin self-lock (same guard as step 1, in case someone calls step 2 directly)
    if current_user.role == UserRole.super_admin:
        raise HTTPException(status_code=403,
            detail="Super Admin account cannot be deleted.")

    if not verify_password(data.password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect password.")

    otp_valid = verify_otp(
        db, phone=current_user.phone, code=data.otp_code,
        purpose=OTPPurpose.account_deletion
    )
    if not otp_valid:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP.")

    # ✅ Anonymize PII while preserving the user row (for FK integrity in posts/votes/etc.)
    current_user.is_active              = False
    current_user.full_name              = "Deleted user"
    current_user.display_name           = "Deleted user"
    current_user.phone                  = f"deleted_{current_user.id}"   # frees the original phone for re-registration
    current_user.profile_photo_url      = None
    current_user.verification_photo_url = None
    current_user.badge                  = "none"
    current_user.is_verified            = False
    current_user.is_durbe_resident      = False
    current_user.verified_by            = None
    current_user.verified_at            = None
    current_user.deleted_at             = datetime.utcnow()
    db.commit()

    return {"message": "Your account has been deleted. Your posts will remain under 'Deleted user'."}


# ─── Vendor + role management ─────────────────────────────────

@router.post("/promote-vendor")
def promote_vendor(
    data: PromoteVendorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Admin promotes an existing user to vendor role.
    User must already have an account. Admin provides
    their phone number + shop name. Password unchanged.
    """
    user = db.query(User).filter(User.phone == data.phone).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="No account found with this phone number."
        )
    if user.role == UserRole.vendor:
        raise HTTPException(
            status_code=400,
            detail=f"{user.full_name} is already a vendor."
        )
    user.role      = UserRole.vendor
    user.shop_name = data.shop_name
    db.commit()
    return {
        "message":   f"{user.full_name} is now a vendor.",
        "shop_name": user.shop_name,
        "phone":     user.phone,
    }

@router.patch("/users/{user_id}/role")
def change_user_role(
    user_id: str,
    data: ChangeRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Super admin changes any user's role. Cannot change another super_admin."""
    if current_user.role != UserRole.super_admin:
        raise HTTPException(status_code=403, detail="Only Super Admin can change roles.")

    allowed = {"user", "admin", "vendor"}
    if data.role not in allowed:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {allowed}")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.role == UserRole.super_admin:
        raise HTTPException(status_code=403, detail="Cannot change Super Admin's role.")

    user.role = UserRole(data.role)
    db.commit()
    return {"message": f"{user.full_name} is now {data.role}."}