# ============================================================
# main.py — Application Entry Point
# ============================================================
# This is the first file FastAPI reads when the server starts.
# It creates the FastAPI app instance and registers everything.
#
# IMPORTS FROM: app/database.py (engine, Base)
#               app/models/user.py (User table)
#               app/models/otp.py  (OTP table)
# IMPORTED BY:  nothing — this is the top of the chain
#
# STARTUP SEQUENCE:
#   1. Models are imported → they register themselves with Base
#   2. create_all() sees all registered models → creates tables
#   3. FastAPI app is created
#   4. Routers are registered (we'll add these soon)
#   5. Server starts listening for requests
# ============================================================

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler                   # ✅ CHANGE
from slowapi.errors import RateLimitExceeded                       # ✅ keep
from app.core.limiter import limiter                               # ✅ CHANGE — import from new file 
from app.database import engine, Base
from app.routers import auth, weather, schemes, contact, guides, gram_awaaz, vikas_prastav, gram_sabha, neta_report_card, vendor_listings, job_alerts, community_members, banners, promises

# Importing models so SQLAlchemy knows they exist before
# create_all() runs. Without these imports, the tables
# would never be created — Base wouldn't know about them.
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

# Create all tables that are registered with Base.
# Safe to run every startup — skips tables that already exist.
Base.metadata.create_all(bind=engine)

# Create the FastAPI app instance.
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
app.include_router(gram_sabha.router)
app.include_router(neta_report_card.router)
app.include_router(vendor_listings.router)
app.include_router(job_alerts.router)
app.include_router(community_members.router)
app.include_router(banners.router)
app.include_router(promises.router)

# Health check endpoint — confirms the server is running.
@app.get("/")
def root():
    return {"message": "Gram Seva API is running 🏡"}
