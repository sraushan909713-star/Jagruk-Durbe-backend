# ============================================================
# main.py — Application Entry Point
# ============================================================

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter
from app.database import engine, Base
from app.routers import (
    auth, weather, schemes, contact, guides, gram_awaaz, vikas_prastav,
    gram_sabha, neta_report_card, vendor_listings, job_alerts,
    community_members, banners, promises,
    items, units,
    uploads
)

# Model imports — required so Alembic --autogenerate sees them.
from app.models import user, otp
from app.models import contact as contact_model
from app.models import scheme as scheme_model
from app.models import guide as guide_model
from app.models import gram_awaaz as gram_awaaz_model
from app.models import vikas_prastav as vikas_prastav_model
from app.models import gram_sabha as gram_sabha_model
from app.models import neta_report_card as neta_report_card_model
from app.models import vendor_listing as vendor_listing_model
from app.models import job_alert as job_alert_model
from app.models import community_member as community_member_model
from app.models import banner as banner_model
from app.models import promise as promise_model
from app.models import item as item_model                           # ✅ NEW
from app.models import unit as unit_model                           # ✅ NEW

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
