# app/routers/contact.py
# ─────────────────────────────────────────────────────────────
# API endpoints for the Local Contacts feature.
#
# PUBLIC (no login needed):
#   GET  /contacts/          → list all contacts (optional filter by category)
#   GET  /contacts/{id}      → get one contact's full details
#
# ADMIN ONLY (JWT token required, role must be admin or super_admin):
#   POST   /contacts/        → add a new contact
#   PUT    /contacts/{id}    → edit an existing contact
#   DELETE /contacts/{id}    → soft delete (hides from app, stays in database)
# ─────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.contact import Contact, ContactCategory
from app.models.user import User
from app.schemas.contact import ContactCreate, ContactUpdate, ContactResponse
from app.core.deps import require_admin

router = APIRouter()
# ─────────────────────────────────────────────────────────────
# PUBLIC ENDPOINTS (no login required)
# ─────────────────────────────────────────────────────────────

@router.get("/", response_model=List[ContactResponse])
def get_all_contacts(
    category: Optional[ContactCategory] = Query(None, description="Filter: emergency / official / health / education"),
    village_id: int = Query(1),
    db: Session = Depends(get_db)
):
    """
    Returns all active contacts for a village.
    Optionally filter by category (emergency, official, health, education).
    No login required — any villager can view contacts.
    Emergency contacts appear first, then alphabetical within each category.
    """
    query = db.query(Contact).filter(
        Contact.is_active == True,
        Contact.village_id == village_id
    )

    if category:
        query = query.filter(Contact.category == category)

    # Emergency contacts first, then alphabetical by name within category
    return query.order_by(Contact.category, Contact.name).all()


@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    """
    Returns full details of a single contact by ID.
    Includes the how_to_talk guide if Admin has written one.
    No login required.
    """
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.is_active == True
    ).first()

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found.")

    return contact


# ─────────────────────────────────────────────────────────────
# ADMIN ENDPOINTS (JWT token required, Admin or Super Admin only)
# ─────────────────────────────────────────────────────────────

@router.post("/", response_model=ContactResponse)
def create_contact(
    data: ContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Admin adds a new contact.
    For official contacts (Mukhiya, BDO etc.) — Admin must have visited
    the person and received their permission before adding.
    For emergency numbers (100, 108) — no permission needed, add directly.
    """
    contact = Contact(**data.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.put("/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: int,
    data: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Updates an existing contact.
    Only Admins and Super Admins can do this.
    Only the fields that are sent will be updated — others stay unchanged.
    """
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.is_active == True
    ).first()

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found.")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)

    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}")
def delete_contact(
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Soft deletes a contact — sets is_active = False.
    The contact stays in the database but disappears from the app.
    Only Admins and Super Admins can do this.
    """
    contact = db.query(Contact).filter(
        Contact.id == contact_id,
        Contact.is_active == True
    ).first()

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found.")

    contact.is_active = False
    db.commit()
    return {"message": f"Contact '{contact.name}' deleted successfully."}