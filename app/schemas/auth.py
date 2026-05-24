# app/schemas/auth.py — Pydantic Models for Authentication

from pydantic import BaseModel, field_validator


# ── Shared validators ────────────────────────────────────────
# Defined once, reused across schemas via the @field_validator hook.

def _validate_phone(v: str) -> str:
    """Phone must be exactly 10 digits, all numeric."""
    v = v.strip()
    if not v.isdigit() or len(v) != 10:
        raise ValueError("Phone number must be exactly 10 digits.")
    return v


def _validate_password(v: str) -> str:
    """Password must be at least 8 characters."""
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters.")
    return v


# ── Request schemas ──────────────────────────────────────────

class SendOTPRequest(BaseModel):
    phone: str
    purpose: str  # "registration" or "login"

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v):
        return _validate_phone(v)


class RegisterRequest(BaseModel):
    phone: str
    name: str
    otp_code: str   # 6-digit code the user received
    password: str   # will be hashed before saving

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v):
        return _validate_phone(v)

    @field_validator("password")
    @classmethod
    def check_password(cls, v):
        return _validate_password(v)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class LoginRequest(BaseModel):
    phone: str
    password: str  # plain text — we'll verify against stored hash

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v):
        return _validate_phone(v)


class ResetPasswordRequest(BaseModel):
    phone: str
    otp_code: str       # OTP sent with purpose="reset_password"
    new_password: str   # will be hashed before saving

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v):
        return _validate_phone(v)

    @field_validator("new_password")
    @classmethod
    def check_password(cls, v):
        return _validate_password(v)