# ============================================================
# database.py — Database Connection Setup
# ============================================================
# Handles both:
#   - SQLite for local dev      (sqlite:///./gramseva.db)
#   - PostgreSQL for production (postgresql://user:pass@host/db)
#
# Railway-style URLs use the legacy "postgres://" prefix; we
# rewrite to "postgresql://" because SQLAlchemy 2.0 requires it.
# ============================================================

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        "Local dev: set it in .env. "
        "Production: set it in Railway env variables."
    )

# Railway / Heroku still use the legacy "postgres://" prefix
# in their auto-generated URLs. SQLAlchemy 2.0+ requires
# "postgresql://" — rewrite transparently.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Engine config differs between the two backends.
if DATABASE_URL.startswith("sqlite"):
    # SQLite in FastAPI's threaded context needs this flag.
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL on Railway — production-grade connection pool.
    #   pool_pre_ping: detect & recycle dropped connections (Railway can
    #                  rotate connections behind the scenes).
    #   pool_size + max_overflow: handle bursts without exhausting the
    #                  free tier's connection limit.
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency. Opens a session per request, closes always."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
