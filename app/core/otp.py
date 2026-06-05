# app/core/otp.py — OTP Generation and Verification Logic
# ============================================================
# This file contains the core logic for creating and verifying OTPs.

import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models.otp import OTP, OTPPurpose  # ✅ import OTPPurpose too since your model has it


def generate_otp_code() -> str:
    """Generate a cryptographically secure random 6-digit OTP, zero-padded (e.g. 004521)."""
    return str(secrets.randbelow(1_000_000)).zfill(6)


def create_otp(db: Session, phone: str, purpose: OTPPurpose) -> str:
    """
    Create a new OTP for a phone number.
    Deletes any previous OTPs for same phone+purpose first.
    Returns the generated code.
    """
    # Delete old OTPs for this phone + purpose to avoid stale codes
    db.query(OTP).filter(
        OTP.phone == phone,
        OTP.purpose == purpose  # ✅ using your purpose field
    ).delete()

    code = generate_otp_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    otp_record = OTP(
        phone=phone,
        otp_code=code,           # ✅ matches your column name: otp_code (not `code`)
        purpose=purpose,         # ✅ matches your purpose column
        is_used=False,           # ✅ matches your is_used column
        expires_at=expires_at,
    )
    db.add(otp_record)
    db.commit()
    return code


def verify_otp(db: Session, phone: str, code: str, purpose: OTPPurpose) -> bool:
    """
    Verify an OTP. Returns True if valid, False if not found/expired/used.
    Marks it as used on success (is_used=True) instead of deleting.
    """
    otp_record = db.query(OTP).filter(
        OTP.phone == phone,
        OTP.otp_code == code,         # ✅ your column name
        OTP.purpose == purpose,        # ✅ your column name
        OTP.is_used == False,          # ✅ your column name
        OTP.expires_at > datetime.now(timezone.utc)
    ).first()

    if not otp_record:
        return False

    # Mark as used instead of deleting — better for audit trail
    otp_record.is_used = True  # ✅ using your is_used field
    db.commit()
    return True