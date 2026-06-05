# app/routers/gram_awaaz.py
# ─────────────────────────────────────────────
# Gram Awaaz — Village Voice
# Villagers raise civic complaints with evidence.
# Anyone can read. Any logged-in user can post or upvote.
# ─────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.gram_awaaz import GramAwaaz, GramAwaazUpvote, Department
from app.models.user import User
from app.schemas.gram_awaaz import (
    GramAwaazCreate, GramAwaazResponse,
    GramAwaazListResponse, UpvoteResponse
)
from app.core.deps import require_admin, require_verified
router = APIRouter(
    prefix="/gram-awaaz",
    tags=["Gram Awaaz"]
)
# ─────────────────────────────────────────────
# PUBLIC ENDPOINTS
# ─────────────────────────────────────────────

@router.get("", response_model=List[GramAwaazListResponse])
def list_posts(
    department: Optional[Department] = Query(None, description="Filter by department"),
    db: Session = Depends(get_db)
):
    """
    Returns all active Gram Awaaz posts.
    Sorted by upvote count — most supported issues appear first.
    No login required — anyone can read complaints.
    """
    query = db.query(GramAwaaz).filter(GramAwaaz.is_active == True)

    if department:
        query = query.filter(GramAwaaz.department == department)

    # ✅ Most upvoted first — pressure rises to the top
    posts = query.order_by(GramAwaaz.upvote_count.desc()).all()
    result = []
    for p in posts:
        user = db.query(User).filter(User.id == p.posted_by).first()
        result.append({
            **{c.key: getattr(p, c.key) for c in p.__table__.columns},
            'poster_name':  user.full_name if user else 'Unknown',
            'poster_photo': user.profile_photo_url if user else None,
        })
    return result


@router.get("/{post_id}", response_model=GramAwaazResponse)
def get_post(post_id: str, db: Session = Depends(get_db)):
    """
    Returns full details of a single complaint post.
    No login required.
    """
    post = db.query(GramAwaaz).filter(
        GramAwaaz.id == post_id,
        GramAwaaz.is_active == True
    ).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    user = db.query(User).filter(User.id == post.posted_by).first()
    return {
        **{c.key: getattr(post, c.key) for c in post.__table__.columns},
        'poster_name':  user.full_name if user else 'Unknown',
        'poster_photo': user.profile_photo_url if user else None,
    }


# ─────────────────────────────────────────────
# LOGGED-IN USER ENDPOINTS
# ─────────────────────────────────────────────

@router.post("", response_model=GramAwaazResponse, status_code=201)
def create_post(
    data: GramAwaazCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verified)
):
    """
    Only verified Durbe Niwasi residents can post complaints.
    Photo is mandatory — enforces evidence-over-emotion principle.
    """
    post = GramAwaaz(
        title=data.title,
        description=data.description,
        location=data.location,
        affected_count=data.affected_count,
        department=data.department,
        demand=data.demand,
        photo_url_1=data.photo_url_1,   # ✅ CHANGE
        photo_url_2=data.photo_url_2,   # ✅ ADD
        photo_url_3=data.photo_url_3,   # ✅ ADD
        photo_url_4=data.photo_url_4,   # ✅ ADD
        posted_by=current_user.id
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.post("/{post_id}/upvote", response_model=UpvoteResponse)
def upvote_post(
    post_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verified)
):
    """
    Upvotes a Gram Awaaz post.
    Each user can only upvote a post once.
    Upvote count is the civic pressure meter — higher = more urgent.
    """
    # Check post exists
    post = db.query(GramAwaaz).filter(
        GramAwaaz.id == post_id,
        GramAwaaz.is_active == True
    ).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    # Check if user already upvoted this post
    existing = db.query(GramAwaazUpvote).filter(
        GramAwaazUpvote.post_id == post_id,
        GramAwaazUpvote.user_id == current_user.id
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="You have already upvoted this post."
        )

    # Record the upvote
    upvote = GramAwaazUpvote(
        post_id=post_id,
        user_id=current_user.id
    )
    db.add(upvote)

    # Increment the counter on the post
    post.upvote_count += 1
    db.commit()

    return UpvoteResponse(
        message="Upvote recorded successfully.",
        upvote_count=post.upvote_count
    )


# ─────────────────────────────────────────────
# ADMIN-ONLY ENDPOINTS
# ─────────────────────────────────────────────

@router.delete("/{post_id}", status_code=200)
def delete_post(
    post_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Soft-deletes a post — only Admin or Super Admin can do this.
    Used to remove fake or abusive posts.
    """
    post = db.query(GramAwaaz).filter(GramAwaaz.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    post.is_active = False
    db.commit()
    return {"message": "Post removed successfully."}