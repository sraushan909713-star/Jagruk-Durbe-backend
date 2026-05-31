# app/core/config.py — Application Configuration

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Auth ─────────────────────────────────────────────
    SECRET_KEY: str                                                              # ✅ no default — must come from .env
    ALGORITHM: str = "HS256"                                                     # non-secret, default OK
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30                              # non-secret, default OK (30 days)

    # ── Database ─────────────────────────────────────────
    DATABASE_URL: str                                                            # ✅ no default

    # ── Cloudinary ───────────────────────────────────────
    cloudinary_cloud_name: str                                                   # ✅ no default
    cloudinary_api_key: str                                                      # ✅ no default
    cloudinary_api_secret: str                                                   # ✅ no default

    class Config:
        env_file = ".env"


settings = Settings()