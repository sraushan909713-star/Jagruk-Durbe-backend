# app/routers/neta_report_card.py
# ─────────────────────────────────────────────────────────────
# Neta Ka Report Card — Rate Your Representative
#
# Endpoint map:
#
#   PUBLIC
#   GET    /neta                          → list all leaders + avg rating
#   GET    /neta/{neta_id}                → leader detail + has_rated flag
#   GET    /neta/{neta_id}/history        → per-cycle avg ratings for graph
#   GET    /neta/window/status            → current window open/closed state
#
#   VERIFIED USER (Durbe Niwasi badge required)
#   POST   /neta/{neta_id}/rate           → submit rating (window must be open)
#
#   ADMIN / SUPER ADMIN
#   POST   /neta/leaders                  → add a new leader
#   PATCH  /neta/leaders/{neta_id}        → update leader details
#   DELETE /neta/leaders/{neta_id}        → soft-delete a leader
#   DELETE /neta/ratings/{rating_id}      → soft-delete a rating (moderation)
#
#   SUPER ADMIN ONLY
#   PATCH  /neta/window/hide              → force-close the active window
#   PATCH  /neta/window/unhide            → re-open a hidden window
# ─────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime, timezone

from app.database import get_db
from app.models.neta_report_card import Neta, RatingWindow, NetaRating
from app.models.user import User
from app.schemas.neta_report_card import (
    NetaCreate, NetaUpdate, NetaResponse, NetaDetailResponse,
    NetaRatingCreate, NetaRatingResponse,
    RatingWindowResponse, NetaHistoryResponse, RatingHistoryPoint
)
from app.core.security import decode_access_token
from app.core.deps import require_admin, require_super_admin, require_verified
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(
    prefix="/neta",
    tags=["Neta Report Card"]
)
def _get_active_window(db: Session) -> RatingWindow | None:
    """
    Returns the currently open rating window, or None.
    A window is open if:
      - now is between opens_at and closes_at
      - is_hidden is False
    """
    now = datetime.now(timezone.utc)
    return db.query(RatingWindow).filter(
        RatingWindow.opens_at  <= now,
        RatingWindow.closes_at >= now,
        RatingWindow.is_hidden == False
    ).first()


def _compute_avg(neta_id: str, db: Session):
    """Returns (avg_stars, total_ratings) for a neta across all windows."""
    result = db.query(
        func.avg(NetaRating.stars),
        func.count(NetaRating.id)
    ).filter(
        NetaRating.neta_id  == neta_id,
        NetaRating.is_active == True
    ).first()
    avg   = round(float(result[0]), 1) if result[0] else None
    total = result[1] or 0
    return avg, total


# ─────────────────────────────────────────────────────────────
# PUBLIC ENDPOINTS
# ─────────────────────────────────────────────────────────────

@router.get("/window/status", response_model=RatingWindowResponse)
def get_window_status(db: Session = Depends(get_db)):
    """
    Returns the current rating window state.
    Flutter uses this to show/hide the rating UI and display countdown.
    """
    now    = datetime.now(timezone.utc)
    window = db.query(RatingWindow).filter(
        RatingWindow.opens_at <= now,
        RatingWindow.closes_at >= now
    ).first()

    if not window:
        # No active window — find the next upcoming one
        window = db.query(RatingWindow).filter(
            RatingWindow.opens_at > now
        ).order_by(RatingWindow.opens_at.asc()).first()

    if not window:
        raise HTTPException(
            status_code=404,
            detail="No rating window is currently scheduled."
        )

    is_open = (
        window.opens_at <= now <= window.closes_at
        and not window.is_hidden
    )

    return RatingWindowResponse(
        id        = window.id,
        label     = window.label,
        opens_at  = window.opens_at,
        closes_at = window.closes_at,
        is_hidden = window.is_hidden,
        is_open   = is_open
    )


@router.get("", response_model=List[NetaResponse])
def list_netas(db: Session = Depends(get_db)):
    """
    Returns all active leaders with their average rating and total rating count.
    No login required — anyone can view.
    """
    netas = db.query(Neta).filter(Neta.is_active == True).all()

    result = []
    for neta in netas:
        avg, total = _compute_avg(neta.id, db)
        result.append(NetaResponse(
            id             = neta.id,
            name           = neta.name,
            designation    = neta.designation,
            party          = neta.party,
            photo_url      = neta.photo_url,
            average_rating = avg,
            total_ratings  = total,
            is_active      = neta.is_active,
            created_at     = neta.created_at
        ))
    return result


@router.get("/{neta_id}", response_model=NetaDetailResponse)
def get_neta_detail(
    neta_id: str,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
):
    """
    Returns full leader detail + average rating.
    If a logged-in user makes this request, also returns has_rated_this_window
    so Flutter knows whether to show or lock the rating UI.
    """
    neta = db.query(Neta).filter(
        Neta.id == neta_id,
        Neta.is_active == True
    ).first()

    if not neta:
        raise HTTPException(status_code=404, detail="Leader not found.")

    avg, total = _compute_avg(neta.id, db)

    # ── Check if current user has rated in active window ──────
    has_rated = False
    if credentials:
        payload = decode_access_token(credentials.credentials)
        if payload:
            user_id = payload.get("sub")
            window  = _get_active_window(db)
            if window:
                existing = db.query(NetaRating).filter(
                    NetaRating.neta_id   == neta_id,
                    NetaRating.window_id == window.id,
                    NetaRating.rated_by  == user_id,
                    NetaRating.is_active == True
                ).first()
                has_rated = existing is not None

    return NetaDetailResponse(
        id                    = neta.id,
        name                  = neta.name,
        designation           = neta.designation,
        party                 = neta.party,
        photo_url             = neta.photo_url,
        average_rating        = avg,
        total_ratings         = total,
        is_active             = neta.is_active,
        created_at            = neta.created_at,
        has_rated_this_window = has_rated
    )


@router.get("/{neta_id}/history", response_model=NetaHistoryResponse)
def get_neta_history(neta_id: str, db: Session = Depends(get_db)):
    """
    Returns per-cycle average ratings for a neta — used to render the
    rating history graph. X-axis = window label, Y-axis = avg stars.
    Only returns closed windows (completed cycles).
    """
    neta = db.query(Neta).filter(
        Neta.id == neta_id,
        Neta.is_active == True
    ).first()

    if not neta:
        raise HTTPException(status_code=404, detail="Leader not found.")

    now = datetime.now(timezone.utc)

    # ── Fetch all closed windows that have at least one rating ─
    closed_windows = db.query(RatingWindow).filter(
        RatingWindow.closes_at < now
    ).order_by(RatingWindow.closes_at.asc()).all()

    history = []
    for window in closed_windows:
        result = db.query(
            func.avg(NetaRating.stars),
            func.count(NetaRating.id)
        ).filter(
            NetaRating.neta_id   == neta_id,
            NetaRating.window_id == window.id,
            NetaRating.is_active == True
        ).first()

        if result[1] and result[1] > 0:   # Only include windows with at least 1 rating
            history.append(RatingHistoryPoint(
                window_label  = window.label,
                average_stars = round(float(result[0]), 1),
                total_ratings = result[1],
                window_closes = window.closes_at
            ))

    return NetaHistoryResponse(
        neta_id   = neta.id,
        neta_name = neta.name,
        history   = history
    )


# ─────────────────────────────────────────────────────────────
# VERIFIED USER ENDPOINTS
# ─────────────────────────────────────────────────────────────

@router.post("/{neta_id}/rate", response_model=NetaRatingResponse, status_code=201)
def submit_rating(
    neta_id: str,
    data: NetaRatingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verified)
):
    """
    Submits a star rating for a neta.
    Rules:
      - User must be Durbe Niwasi (verified)
      - A rating window must be currently open
      - One submission per user per neta per window — locked after submit
    """
    # ── Leader must exist ─────────────────────────────────────
    neta = db.query(Neta).filter(
        Neta.id == neta_id,
        Neta.is_active == True
    ).first()
    if not neta:
        raise HTTPException(status_code=404, detail="Leader not found.")

    # ── Rating window must be open ────────────────────────────
    window = _get_active_window(db)
    if not window:
        raise HTTPException(
            status_code=400,
            detail="Rating window is currently closed. Please wait for the next window."
        )

    # ── One rating per user per neta per window ───────────────
    existing = db.query(NetaRating).filter(
        NetaRating.neta_id   == neta_id,
        NetaRating.window_id == window.id,
        NetaRating.rated_by  == current_user.id,
        NetaRating.is_active == True
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"You have already rated {neta.name} in the {window.label} window."
        )

    # ── Save rating ───────────────────────────────────────────
    rating = NetaRating(
        neta_id   = neta_id,
        window_id = window.id,
        rated_by  = current_user.id,
        stars     = data.stars
    )
    db.add(rating)
    db.commit()
    db.refresh(rating)
    return rating


# ─────────────────────────────────────────────────────────────
# ADMIN ENDPOINTS — Leader management
# ─────────────────────────────────────────────────────────────

@router.post("/leaders", response_model=NetaResponse, status_code=201)
def add_neta(
    data: NetaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Admin adds a new leader to the system."""
    neta = Neta(
        name        = data.name,
        designation = data.designation,
        party       = data.party,
        photo_url   = data.photo_url
    )
    db.add(neta)
    db.commit()
    db.refresh(neta)
    return NetaResponse(
        id             = neta.id,
        name           = neta.name,
        designation    = neta.designation,
        party          = neta.party,
        photo_url      = neta.photo_url,
        average_rating = None,
        total_ratings  = 0,
        is_active      = neta.is_active,
        created_at     = neta.created_at
    )


@router.patch("/leaders/{neta_id}", response_model=NetaResponse)
def update_neta(
    neta_id: str,
    data: NetaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Admin updates leader details (name, photo, party, designation)."""
    neta = db.query(Neta).filter(Neta.id == neta_id).first()
    if not neta:
        raise HTTPException(status_code=404, detail="Leader not found.")

    if data.name        is not None: neta.name        = data.name
    if data.designation is not None: neta.designation = data.designation
    if data.party       is not None: neta.party       = data.party
    if data.photo_url   is not None: neta.photo_url   = data.photo_url

    db.commit()
    db.refresh(neta)
    avg, total = _compute_avg(neta.id, db)
    return NetaResponse(
        id             = neta.id,
        name           = neta.name,
        designation    = neta.designation,
        party          = neta.party,
        photo_url      = neta.photo_url,
        average_rating = avg,
        total_ratings  = total,
        is_active      = neta.is_active,
        created_at     = neta.created_at
    )


@router.delete("/leaders/{neta_id}", status_code=200)
def delete_neta(
    neta_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Soft-deletes a leader. Their ratings are preserved for historical records."""
    neta = db.query(Neta).filter(Neta.id == neta_id).first()
    if not neta:
        raise HTTPException(status_code=404, detail="Leader not found.")
    neta.is_active = False
    db.commit()
    return {"message": f"{neta.name} removed from the report card."}


@router.delete("/ratings/{rating_id}", status_code=200)
def delete_rating(
    rating_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Soft-deletes a rating — moderation tool for Admin/Super Admin."""
    rating = db.query(NetaRating).filter(NetaRating.id == rating_id).first()
    if not rating:
        raise HTTPException(status_code=404, detail="Rating not found.")
    rating.is_active = False
    db.commit()
    return {"message": "Rating removed successfully."}


# ─────────────────────────────────────────────────────────────
# SUPER ADMIN ENDPOINTS — Window control
# ─────────────────────────────────────────────────────────────

@router.post("/window", status_code=201)
def create_window(
    label: str,
    opens_at: datetime,
    closes_at: datetime,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Super Admin manually creates a rating window.
    Normally windows are auto-generated, but this allows custom scheduling.
    """
    window = RatingWindow(
        label     = label,
        opens_at  = opens_at,
        closes_at = closes_at,
        is_hidden = False
    )
    db.add(window)
    db.commit()
    db.refresh(window)
    return {"message": f"Rating window '{label}' created.", "window_id": window.id}


@router.patch("/window/hide", status_code=200)
def hide_window(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Super Admin force-closes the currently active window.
    Use when you want to stop rating before the 10-day window ends.
    """
    window = _get_active_window(db)
    if not window:
        raise HTTPException(status_code=404, detail="No active window to hide.")
    window.is_hidden = True
    db.commit()
    return {"message": f"Rating window '{window.label}' has been hidden."}


@router.patch("/window/unhide", status_code=200)
def unhide_window(
    window_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Super Admin re-opens a previously hidden window (if still within schedule)."""
    window = db.query(RatingWindow).filter(RatingWindow.id == window_id).first()
    if not window:
        raise HTTPException(status_code=404, detail="Window not found.")
    window.is_hidden = False
    db.commit()
    return {"message": f"Rating window '{window.label}' is now visible again."}