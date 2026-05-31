# app/routers/uploads.py
# ─────────────────────────────────────────────────────────────
# Authenticated photo upload endpoint with NSFW filtering.
#
# Flow:  multipart upload → MIME + size check → NSFW classifier
#        → Cloudinary upload (signed) → return secure URL.
#
# All photo uploads in the app go through here. Gram Awaaz,
# Vikas Prastav, profile photos, future Mandi photos — they all
# call this endpoint instead of hitting Cloudinary directly.
# ─────────────────────────────────────────────────────────────
from app.core.config import settings                                    # ✅ NEW
import logging
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

import cloudinary
import cloudinary.uploader

from app.database import get_db
from app.models.user import User
from app.core.security import decode_access_token
from app.core.nsfw_detector import is_image_safe

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["Uploads"])

cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,                          # ✅
    api_key=settings.cloudinary_api_key,                                # ✅
    api_secret=settings.cloudinary_api_secret,                          # ✅
    secure=True,
)

# ── Upload constraints ────────────────────────────────────
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


# ─────────────────────────────────────────────────────────────
# POST /uploads/photo
# ─────────────────────────────────────────────────────────────
@router.post("/photo")
async def upload_photo(
    file: UploadFile = File(...),
    folder: Optional[str] = Form("jagruk_durbe"),
    current_user: User = Depends(get_current_user),
):
    """
    Authenticated photo upload with NSFW filtering.
    Returns {url, public_id, width, height} on success.
    Returns 400 with friendly message on any rejection.
    """
    # ── Validate MIME ─────────────────────────────────────
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG, and WEBP images are allowed.",
        )

    # ── Read bytes ────────────────────────────────────────
    contents = await file.read()

    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Empty file.")

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Image too large. Max size is {MAX_FILE_SIZE // (1024 * 1024)}MB.",
        )

    # ── NSFW check ────────────────────────────────────────
    is_safe, reason = is_image_safe(contents)
    if not is_safe:
        logger.info(f"User {current_user.id} upload rejected: {reason}")
        raise HTTPException(
            status_code=400,
            detail="This image cannot be uploaded — it contains inappropriate content.",
        )

    # ── Upload to Cloudinary ──────────────────────────────
    try:
        result = cloudinary.uploader.upload(
            BytesIO(contents),
            folder=folder,
            resource_type="image",
            transformation=[
                {"quality": "auto", "fetch_format": "auto"},
            ],
            eager=[{"width": 1600, "crop": "limit"}],
        )
        return {
            "url": result["secure_url"],
            "public_id": result["public_id"],
            "width": result.get("width"),
            "height": result.get("height"),
        }
    except Exception as e:
        logger.error(f"Cloudinary upload failed: {e}")
        raise HTTPException(
            status_code=502,
            detail="Image upload failed. Please try again.",
        )