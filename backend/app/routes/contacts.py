"""Contact management routes -- Donors, Vendors, Volunteers."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, require_permission, get_subsidiary_scope, write_audit_log

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


class ContactCreate(BaseModel):
    contact_type: str
    name: str
    email: str | None = None
    phone: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    zip_code: str | None = None
    subsidiary_id: uuid.UUID | None = None
    notes: str | None = None


class ContactUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address_line_1: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    zip_code: str | None = None
    notes: str | None = None
    is_active: bool | None = None


@router.get("")
async def list_contacts(
    contact_type: str | None = Query(None),
    search: str | None = Query(None),
    subsidiary_id: uuid.UUID | None = Query(None),
    is_active: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("contacts.view")),
):
    from app.models.contact import Contact

    count_stmt = select(func.count(Contact.id)).where(Contact.is_active == is_active)
    data_stmt = select(Contact).where(Contact.is_active == is_active)

    if contact_type:
        count_stmt = count_stmt.where(Contact.contact_type == contact_type)
        data_stmt = data_stmt.where(Contact.contact_type == contact_type)

    if subsidiary_id:
        count_stmt = count_stmt.where(Contact.subsidiary_id == subsidiary_id)
        data_stmt = data_stmt.where(Contact.subsidiary_id == subsidiary_id)

    if not subsidiary_id:
        scope = get_subsidiary_scope(_user)
        if scope:
            count_stmt = count_stmt.where(Contact.subsidiary_id == scope)
            data_stmt = data_stmt.where(Contact.subsidiary_id == scope)

    if search:
        like = f"%{search}%"
        search_filter = or_(Contact.name.ilike(like), Contact.email.ilike(like))
        count_stmt = count_stmt.where(search_filter)
        data_stmt = data_stmt.where(search_filter)

    total = (await db.execute(count_stmt)).scalar_one()
    data_stmt = data_stmt.order_by(Contact.name).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(data_stmt)
    contacts = result.scalars().all()

    items = []
    for c in contacts:
        items.append({
            "id": str(c.id),
            "contact_type": c.contact_type,
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "city": c.city,
            "state": c.state,
            "country": c.country,
            "subsidiary_id": str(c.subsidiary_id) if c.subsidiary_id else None,
            "is_active": c.is_active,
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{contact_id}")
async def get_contact(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("contacts.view")),
):
    from app.models.contact import Contact

    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Contact not found")

    return {
        "id": str(c.id),
        "contact_type": c.contact_type,
        "name": c.name,
        "email": c.email,
        "phone": c.phone,
        "address_line_1": c.address_line_1,
        "address_line_2": c.address_line_2,
        "city": c.city,
        "state": c.state,
        "country": c.country,
        "zip_code": c.zip_code,
        "subsidiary_id": str(c.subsidiary_id) if c.subsidiary_id else None,
        "notes": c.notes,
        "is_active": c.is_active,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.post("", status_code=201)
async def create_contact(
    body: ContactCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("contacts.create")),
):
    from app.models.contact import Contact

    contact = Contact(
        contact_type=body.contact_type,
        name=body.name,
        email=body.email,
        phone=body.phone,
        address_line_1=body.address_line_1,
        address_line_2=body.address_line_2,
        city=body.city,
        state=body.state,
        country=body.country,
        zip_code=body.zip_code,
        subsidiary_id=body.subsidiary_id,
        notes=body.notes,
    )
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    await write_audit_log(db, _user, "contact.create", "contact", str(contact.id), {"name": body.name, "contact_type": body.contact_type})
    return {"id": str(contact.id), "name": contact.name, "contact_type": contact.contact_type}


@router.put("/{contact_id}")
async def update_contact(
    contact_id: uuid.UUID,
    body: ContactUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("contacts.update")),
):
    from app.models.contact import Contact

    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    for field in ["name", "email", "phone", "address_line_1", "city", "state", "country", "zip_code", "notes", "is_active"]:
        val = getattr(body, field, None)
        if val is not None:
            setattr(contact, field, val)

    await db.commit()
    await write_audit_log(db, _user, "contact.update", "contact", str(contact_id), body.dict(exclude_unset=True))
    return {"status": "updated"}
