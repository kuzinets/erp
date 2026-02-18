"""Organization routes -- Subsidiaries, Departments, Fiscal Periods."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, require_permission, get_subsidiary_scope, write_audit_log

router = APIRouter(prefix="/api/org", tags=["organization"])


# ---------------------------------------------------------------------------
# SUBSIDIARIES
# ---------------------------------------------------------------------------

class SubsidiaryCreate(BaseModel):
    code: str
    name: str
    parent_id: uuid.UUID | None = None
    currency: str = "USD"
    timezone: str = "UTC"
    address: str | None = None
    library_entity_code: str | None = None


class SubsidiaryUpdate(BaseModel):
    name: str | None = None
    currency: str | None = None
    timezone: str | None = None
    address: str | None = None
    is_active: bool | None = None
    library_entity_code: str | None = None


@router.get("/subsidiaries")
async def list_subsidiaries(
    is_active: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("org.subsidiaries.view")),
):
    from app.models.org import Subsidiary

    stmt = select(Subsidiary).where(Subsidiary.is_active == is_active).order_by(Subsidiary.code)
    result = await db.execute(stmt)
    subs = result.scalars().all()

    items = []
    for s in subs:
        items.append({
            "id": str(s.id),
            "code": s.code,
            "name": s.name,
            "parent_id": str(s.parent_id) if s.parent_id else None,
            "currency": s.currency,
            "timezone": s.timezone,
            "address": s.address,
            "is_active": s.is_active,
            "library_entity_code": s.library_entity_code,
        })

    return {"items": items, "total": len(items)}


@router.get("/subsidiaries/{sub_id}")
async def get_subsidiary(
    sub_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("org.subsidiaries.view")),
):
    from app.models.org import Subsidiary

    result = await db.execute(select(Subsidiary).where(Subsidiary.id == sub_id))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Subsidiary not found")

    return {
        "id": str(s.id),
        "code": s.code,
        "name": s.name,
        "parent_id": str(s.parent_id) if s.parent_id else None,
        "currency": s.currency,
        "timezone": s.timezone,
        "address": s.address,
        "is_active": s.is_active,
        "library_entity_code": s.library_entity_code,
    }


@router.post("/subsidiaries", status_code=201)
async def create_subsidiary(
    body: SubsidiaryCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("org.subsidiaries.create")),
):
    from app.models.org import Subsidiary

    sub = Subsidiary(
        code=body.code,
        name=body.name,
        parent_id=body.parent_id,
        currency=body.currency,
        timezone=body.timezone,
        address=body.address,
        library_entity_code=body.library_entity_code,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    await write_audit_log(db, _user, "org.subsidiary.create", "subsidiary", str(sub.id), {"code": body.code})
    return {"id": str(sub.id), "code": sub.code, "name": sub.name}


@router.put("/subsidiaries/{sub_id}")
async def update_subsidiary(
    sub_id: uuid.UUID,
    body: SubsidiaryUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("org.subsidiaries.update")),
):
    from app.models.org import Subsidiary

    result = await db.execute(select(Subsidiary).where(Subsidiary.id == sub_id))
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Subsidiary not found")

    for field in ["name", "currency", "timezone", "address", "is_active", "library_entity_code"]:
        val = getattr(body, field, None)
        if val is not None:
            setattr(sub, field, val)

    await db.commit()
    await write_audit_log(db, _user, "org.subsidiary.update", "subsidiary", str(sub_id), body.dict(exclude_unset=True))
    return {"status": "updated"}


# ---------------------------------------------------------------------------
# FISCAL PERIODS
# ---------------------------------------------------------------------------

@router.get("/fiscal-years")
async def list_fiscal_years(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("org.fiscal_periods.view")),
):
    from app.models.org import FiscalYear

    stmt = select(FiscalYear).order_by(FiscalYear.start_date.desc())
    result = await db.execute(stmt)
    years = result.scalars().all()

    return {
        "items": [
            {
                "id": str(fy.id),
                "name": fy.name,
                "start_date": str(fy.start_date),
                "end_date": str(fy.end_date),
                "is_closed": fy.is_closed,
            }
            for fy in years
        ]
    }


@router.get("/fiscal-periods")
async def list_fiscal_periods(
    fiscal_year_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("org.fiscal_periods.view")),
):
    from app.models.org import FiscalPeriod

    stmt = select(FiscalPeriod)
    if fiscal_year_id:
        stmt = stmt.where(FiscalPeriod.fiscal_year_id == fiscal_year_id)
    if status:
        stmt = stmt.where(FiscalPeriod.status == status)
    stmt = stmt.order_by(FiscalPeriod.period_code)

    result = await db.execute(stmt)
    periods = result.scalars().all()

    return {
        "items": [
            {
                "id": str(p.id),
                "fiscal_year_id": str(p.fiscal_year_id),
                "period_code": p.period_code,
                "period_name": p.period_name,
                "start_date": str(p.start_date),
                "end_date": str(p.end_date),
                "status": p.status,
            }
            for p in periods
        ]
    }


@router.post("/fiscal-periods/{period_id}/close")
async def close_fiscal_period(
    period_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("org.fiscal_periods.close")),
):
    from app.models.org import FiscalPeriod

    result = await db.execute(select(FiscalPeriod).where(FiscalPeriod.id == period_id))
    period = result.scalar_one_or_none()
    if not period:
        raise HTTPException(status_code=404, detail="Fiscal period not found")

    if period.status == "closed":
        raise HTTPException(status_code=422, detail="Period is already closed")

    period.status = "closed"
    await db.commit()
    await write_audit_log(db, _user, "org.fiscal_period.close", "fiscal_period", str(period_id), {"period_code": period.period_code})
    return {"status": "closed", "period_code": period.period_code}


@router.post("/fiscal-periods/{period_id}/reopen")
async def reopen_fiscal_period(
    period_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("org.fiscal_periods.reopen")),
):
    from app.models.org import FiscalPeriod

    result = await db.execute(select(FiscalPeriod).where(FiscalPeriod.id == period_id))
    period = result.scalar_one_or_none()
    if not period:
        raise HTTPException(status_code=404, detail="Fiscal period not found")

    period.status = "adjusting"
    await db.commit()
    await write_audit_log(db, _user, "org.fiscal_period.reopen", "fiscal_period", str(period_id), {"period_code": period.period_code})
    return {"status": "adjusting", "period_code": period.period_code}


# ---------------------------------------------------------------------------
# DEPARTMENTS
# ---------------------------------------------------------------------------

@router.get("/departments")
async def list_departments(
    subsidiary_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("org.departments.view")),
):
    from app.models.org import Department

    stmt = select(Department)
    if subsidiary_id:
        stmt = stmt.where(Department.subsidiary_id == subsidiary_id)

    if not subsidiary_id:
        scope = get_subsidiary_scope(_user)
        if scope:
            stmt = stmt.where(Department.subsidiary_id == scope)

    stmt = stmt.order_by(Department.code)

    result = await db.execute(stmt)
    depts = result.scalars().all()

    return {
        "items": [
            {
                "id": str(d.id),
                "subsidiary_id": str(d.subsidiary_id),
                "code": d.code,
                "name": d.name,
                "is_active": d.is_active,
            }
            for d in depts
        ]
    }


@router.post("/departments", status_code=201)
async def create_department(
    body: dict,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("org.departments.create")),
):
    from app.models.org import Department

    dept = Department(
        subsidiary_id=uuid.UUID(body["subsidiary_id"]),
        code=body["code"],
        name=body["name"],
    )
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    await write_audit_log(db, _user, "org.department.create", "department", str(dept.id), {"code": body["code"]})
    return {"id": str(dept.id), "code": dept.code, "name": dept.name}
