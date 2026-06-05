# ============================================================
# main.py — Application Entry Point
# ============================================================

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter
from app.routers import (
    auth, weather, schemes, contact, guides, gram_awaaz, vikas_prastav,
    neta_report_card, vendor_listings, job_alerts,
    community_members, banners, promises,
    items, units,
    uploads
)

# Note: Model imports for Alembic registration live in migrations/env.py.
# main.py does not need to import models — routers import them as needed,
# and SQLAlchemy registers them with Base on first import.

app = FastAPI(
    title="Gram Seva API",
    version="1.0.0",
    description="Backend API for Gram Seva — Jagruk Durbe"
)

# ── Rate limiter ────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth.router)
app.include_router(weather.router)
app.include_router(schemes.router)
app.include_router(contact.router, prefix="/contacts", tags=["Contacts"])
app.include_router(guides.router)
app.include_router(gram_awaaz.router)
app.include_router(vikas_prastav.router)
# app.include_router(gram_sabha.router)
app.include_router(neta_report_card.router)
app.include_router(items.router)
app.include_router(units.router)
app.include_router(uploads.router)                                                  # ✅ NEW
app.include_router(vendor_listings.router)
app.include_router(job_alerts.router)
app.include_router(community_members.router)
app.include_router(banners.router)
app.include_router(promises.router)


@app.get("/")
def root():
    return {"message": "Gram Seva API is running 🏡"}
