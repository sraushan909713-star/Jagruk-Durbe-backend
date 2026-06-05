# app/routers/promises.py
# ─────────────────────────────────────────────────────────────
# Promises (Neta ke Vaade) API
#
# Endpoint map:
#
#   PUBLIC
#   GET  /promises                    → list all active promises
#   GET  /promises/{id}               → single promise detail
#   GET  /promises/{id}/witnesses     → list of witnesses (name + photo)
#
#   DURBE NIWASI (verified residents only)
#   POST /promises/{id}/witness       → tap to confirm "I witnessed this"
#
#   ADMIN / SUPER ADMIN
#   POST   /promises                  → add a new promise
#   PATCH  /promises/{id}/status      → update status (pending/fulfilled/half_delivered/broken)
#   DELETE /promises/{id}             → soft-delete
# ─────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.promise import Promise, PromiseWitness
from app.models.user import User
from app.schemas.promise import (
    PromiseCreate, PromiseStatusUpdate,
    PromiseResponse, WitnessResponse
)
from app.core.security import decode_access_token
from app.core.deps import get_current_user, require_admin, require_verified
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(
    prefix="/promises",
    tags=["Promises"]
)
def _build_response(
    promise: Promise,
    db: Session,
    current_user_id: str | None = None
) -> PromiseResponse:
    """Builds a PromiseResponse with computed witness_count and has_witnessed."""
    witness_count = db.query(PromiseWitness).filter(
        PromiseWitness.promise_id == promise.id
    ).count()

    has_witnessed = False
    if current_user_id:
        has_witnessed = db.query(PromiseWitness).filter(
            PromiseWitness.promise_id == promise.id,
            PromiseWitness.user_id    == current_user_id
        ).first() is not None

    return PromiseResponse(
        id                = promise.id,
        leader_name       = promise.leader_name,
        leader_role       = promise.leader_role,
        promise_text      = promise.promise_text,
        made_where        = promise.made_where,
        made_where_detail = promise.made_where_detail,
        made_on           = promise.made_on,
        deadline          = promise.deadline,
        crowd_count       = promise.crowd_count,
        status            = promise.status,
        created_by        = promise.created_by,
        witness_count     = witness_count,
        has_witnessed     = has_witnessed,
        is_active         = promise.is_active,
        created_at        = promise.created_at,
    )


# ─────────────────────────────────────────────────────────────
# PUBLIC ENDPOINTS
# ─────────────────────────────────────────────────────────────

@router.get("", response_model=List[PromiseResponse])
def list_promises(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
):
    """
    Returns all active promises, newest first.
    If a logged-in user calls this, has_witnessed is populated per promise.
    """
    promises = db.query(Promise).filter(
        Promise.is_active == True
    ).order_by(Promise.created_at.desc()).all()

    current_user_id = None
    if credentials:
        payload = decode_access_token(credentials.credentials)
        if payload:
            current_user_id = payload.get("sub")

    return [_build_response(p, db, current_user_id) for p in promises]


@router.get("/{promise_id}", response_model=PromiseResponse)
def get_promise(
    promise_id: str,
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
):
    """Returns a single promise with witness count and has_witnessed."""
    promise = db.query(Promise).filter(
        Promise.id        == promise_id,
        Promise.is_active == True
    ).first()
    if not promise:
        raise HTTPException(status_code=404, detail="Promise not found.")

    current_user_id = None
    if credentials:
        payload = decode_access_token(credentials.credentials)
        if payload:
            current_user_id = payload.get("sub")

    return _build_response(promise, db, current_user_id)


@router.get("/{promise_id}/witnesses", response_model=List[WitnessResponse])
def get_witnesses(
    promise_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns full list of witnesses for a promise.
    Shows name + photo — no phone (privacy).
    Public — everyone can see who confirmed.
    This builds social pressure on the leader.
    """
    promise = db.query(Promise).filter(
        Promise.id == promise_id,
        Promise.is_active == True
    ).first()
    if not promise:
        raise HTTPException(status_code=404, detail="Promise not found.")

    witnesses = db.query(PromiseWitness).filter(
        PromiseWitness.promise_id == promise_id
    ).order_by(PromiseWitness.witnessed_at.asc()).all()

    result = []
    for w in witnesses:
        user = db.query(User).filter(User.id == w.user_id).first()
        if user:
            result.append(WitnessResponse(
                id           = w.id,
                user_id      = w.user_id,
                full_name    = user.full_name or user.display_name or "Unknown",
                photo_url    = user.profile_photo_url,
                witnessed_at = w.witnessed_at,
            ))
    return result


# ─────────────────────────────────────────────────────────────
# DURBE NIWASI ENDPOINTS
# ─────────────────────────────────────────────────────────────

@router.post("/{promise_id}/witness", status_code=201)
def witness_promise(
    promise_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verified)
):
    """
    Verified resident confirms they witnessed this promise.
    One tap per user — irreversible (no undo).
    DB UniqueConstraint also prevents double-tap at DB level.
    """
    promise = db.query(Promise).filter(
        Promise.id        == promise_id,
        Promise.is_active == True
    ).first()
    if not promise:
        raise HTTPException(status_code=404, detail="Promise not found.")

    # ── Already witnessed? ────────────────────────────────────
    existing = db.query(PromiseWitness).filter(
        PromiseWitness.promise_id == promise_id,
        PromiseWitness.user_id    == current_user.id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="You have already confirmed this promise."
        )

    witness = PromiseWitness(
        promise_id = promise_id,
        user_id    = current_user.id,
    )
    db.add(witness)
    db.commit()

    # Return updated witness count
    count = db.query(PromiseWitness).filter(
        PromiseWitness.promise_id == promise_id
    ).count()
    return {"message": "You have confirmed this promise.", "witness_count": count}


# ─────────────────────────────────────────────────────────────
# ADMIN ENDPOINTS
# ─────────────────────────────────────────────────────────────

@router.post("", response_model=PromiseResponse, status_code=201)
def create_promise(
    data: PromiseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Admin adds a new promise made by a leader."""
    promise = Promise(
        leader_name       = data.leader_name,
        leader_role       = data.leader_role,
        promise_text      = data.promise_text,
        made_where        = data.made_where,
        made_where_detail = data.made_where_detail,
        made_on           = data.made_on,
        deadline          = data.deadline,
        crowd_count       = data.crowd_count,
        status            = "pending",
        created_by        = current_user.id,
        village_id        = 1,
    )
    db.add(promise)
    db.commit()
    db.refresh(promise)
    return _build_response(promise, db)


@router.patch("/{promise_id}/status", response_model=PromiseResponse)
def update_status(
    promise_id: str,
    data: PromiseStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Updates the promise status.
    Only the admin who created it OR super_admin can change status.
    """
    promise = db.query(Promise).filter(
        Promise.id        == promise_id,
        Promise.is_active == True
    ).first()
    if not promise:
        raise HTTPException(status_code=404, detail="Promise not found.")

    # ── Only poster or super_admin can update status ──────────
    is_poster      = promise.created_by == current_user.id
    is_super_admin = current_user.role == "super_admin"
    if not (is_poster or is_super_admin):
        raise HTTPException(
            status_code=403,
            detail="Only the admin who created this promise or Super Admin can update its status."
        )

    promise.status = data.status
    db.commit()
    db.refresh(promise)
    return _build_response(promise, db, current_user.id)


@router.delete("/{promise_id}", status_code=200)
def delete_promise(
    promise_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Soft-deletes a promise.
    Only the admin who created it OR super_admin can delete.
    """
    promise = db.query(Promise).filter(
        Promise.id == promise_id
    ).first()
    if not promise:
        raise HTTPException(status_code=404, detail="Promise not found.")

    is_poster      = promise.created_by == current_user.id
    is_super_admin = current_user.role == "super_admin"
    if not (is_poster or is_super_admin):
        raise HTTPException(
            status_code=403,
            detail="Only the admin who created this promise or Super Admin can delete it."
        )

    promise.is_active = False
    db.commit()
    return {"message": "Promise deleted successfully."}