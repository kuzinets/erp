"""General Ledger routes — Chart of Accounts, Journal Entries, Trial Balance."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import get_current_user, require_role

router = APIRouter(prefix="/api/gl", tags=["general-ledger"])


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class AccountOut(BaseModel):
    id: uuid.UUID
    account_number: str
    name: str
    account_type: str
    normal_balance: str
    parent_id: uuid.UUID | None = None
    fund_id: uuid.UUID | None = None
    is_active: bool
    description: str | None = None
    balance: float = 0.0
    children: list[AccountOut] = []

    class Config:
        from_attributes = True


class AccountCreate(BaseModel):
    account_number: str
    name: str
    account_type: str
    normal_balance: str
    parent_id: uuid.UUID | None = None
    fund_id: uuid.UUID | None = None
    description: str | None = None

    @field_validator("account_type")
    @classmethod
    def validate_account_type(cls, v):
        if v not in ("asset", "liability", "equity", "revenue", "expense"):
            raise ValueError("Must be asset, liability, equity, revenue, or expense")
        return v

    @field_validator("normal_balance")
    @classmethod
    def validate_normal_balance(cls, v):
        if v not in ("debit", "credit"):
            raise ValueError("Must be debit or credit")
        return v


class AccountUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    fund_id: uuid.UUID | None = None


class JournalLineIn(BaseModel):
    account_id: uuid.UUID
    debit_amount: float = 0.0
    credit_amount: float = 0.0
    memo: str | None = None
    department_id: uuid.UUID | None = None
    fund_id: uuid.UUID | None = None
    cost_center: str | None = None
    quantity: float | None = None


class JournalEntryCreate(BaseModel):
    subsidiary_id: uuid.UUID
    entry_date: date
    memo: str | None = None
    lines: list[JournalLineIn]
    auto_post: bool = False  # Post immediately if True


class JournalLineOut(BaseModel):
    id: uuid.UUID
    line_number: int
    account_id: uuid.UUID
    account_number: str | None = None
    account_name: str | None = None
    debit_amount: float
    credit_amount: float
    memo: str | None = None
    department_id: uuid.UUID | None = None
    fund_id: uuid.UUID | None = None
    cost_center: str | None = None
    quantity: float | None = None

    class Config:
        from_attributes = True


class JournalEntryOut(BaseModel):
    id: uuid.UUID
    entry_number: int
    subsidiary_id: uuid.UUID
    subsidiary_name: str | None = None
    fiscal_period_id: uuid.UUID
    fiscal_period_code: str | None = None
    entry_date: date
    memo: str | None = None
    source: str
    source_reference: str | None = None
    status: str
    posted_at: str | None = None
    created_at: str
    total_debits: float = 0.0
    total_credits: float = 0.0
    lines: list[JournalLineOut] = []

    class Config:
        from_attributes = True


class TrialBalanceItem(BaseModel):
    account_number: str
    account_name: str
    account_type: str
    debit_balance: float
    credit_balance: float


class TrialBalanceResponse(BaseModel):
    fiscal_period: str
    subsidiary_id: uuid.UUID | None = None
    items: list[TrialBalanceItem]
    total_debits: float
    total_credits: float


# ---------------------------------------------------------------------------
# CHART OF ACCOUNTS
# ---------------------------------------------------------------------------

@router.get("/accounts")
async def list_accounts(
    account_type: str | None = Query(None),
    is_active: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.gl import Account

    stmt = select(Account).where(Account.is_active == is_active)
    if account_type:
        stmt = stmt.where(Account.account_type == account_type)
    stmt = stmt.order_by(Account.account_number)

    result = await db.execute(stmt)
    accounts = result.scalars().all()

    items = []
    for a in accounts:
        items.append({
            "id": str(a.id),
            "account_number": a.account_number,
            "name": a.name,
            "account_type": a.account_type,
            "normal_balance": a.normal_balance,
            "parent_id": str(a.parent_id) if a.parent_id else None,
            "fund_id": str(a.fund_id) if a.fund_id else None,
            "is_active": a.is_active,
            "description": a.description,
        })

    return {"items": items, "total": len(items)}


@router.get("/accounts/tree")
async def get_accounts_tree(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Return chart of accounts as a nested tree."""
    from app.models.gl import Account

    stmt = select(Account).where(Account.is_active == True).order_by(Account.account_number)
    result = await db.execute(stmt)
    accounts = result.scalars().all()

    # Build tree
    account_map = {}
    for a in accounts:
        account_map[a.id] = {
            "id": str(a.id),
            "account_number": a.account_number,
            "name": a.name,
            "account_type": a.account_type,
            "normal_balance": a.normal_balance,
            "description": a.description,
            "children": [],
        }

    roots = []
    for a in accounts:
        node = account_map[a.id]
        if a.parent_id and a.parent_id in account_map:
            account_map[a.parent_id]["children"].append(node)
        else:
            roots.append(node)

    return {"items": roots}


@router.get("/accounts/{account_id}")
async def get_account(
    account_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.gl import Account

    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return {
        "id": str(account.id),
        "account_number": account.account_number,
        "name": account.name,
        "account_type": account.account_type,
        "normal_balance": account.normal_balance,
        "parent_id": str(account.parent_id) if account.parent_id else None,
        "fund_id": str(account.fund_id) if account.fund_id else None,
        "is_active": account.is_active,
        "description": account.description,
    }


@router.post("/accounts", status_code=201)
async def create_account(
    body: AccountCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("admin")),
):
    from app.models.gl import Account

    account = Account(
        account_number=body.account_number,
        name=body.name,
        account_type=body.account_type,
        normal_balance=body.normal_balance,
        parent_id=body.parent_id,
        fund_id=body.fund_id,
        description=body.description,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)

    return {"id": str(account.id), "account_number": account.account_number, "name": account.name}


@router.put("/accounts/{account_id}")
async def update_account(
    account_id: uuid.UUID,
    body: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_role("admin")),
):
    from app.models.gl import Account

    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if body.name is not None:
        account.name = body.name
    if body.description is not None:
        account.description = body.description
    if body.is_active is not None:
        account.is_active = body.is_active
    if body.fund_id is not None:
        account.fund_id = body.fund_id

    await db.commit()
    return {"status": "updated"}


# ---------------------------------------------------------------------------
# JOURNAL ENTRIES
# ---------------------------------------------------------------------------

@router.get("/journal-entries")
async def list_journal_entries(
    subsidiary_id: uuid.UUID | None = Query(None),
    fiscal_period: str | None = Query(None),
    je_status: str | None = Query(None, alias="status"),
    source: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.gl import JournalEntry, JournalLine
    from app.models.org import FiscalPeriod, Subsidiary

    # Count query
    count_stmt = select(func.count(JournalEntry.id))
    # Data query
    data_stmt = (
        select(JournalEntry)
        .options(
            selectinload(JournalEntry.subsidiary),
            selectinload(JournalEntry.fiscal_period),
            selectinload(JournalEntry.lines).selectinload(JournalLine.account),
        )
    )

    if subsidiary_id:
        count_stmt = count_stmt.where(JournalEntry.subsidiary_id == subsidiary_id)
        data_stmt = data_stmt.where(JournalEntry.subsidiary_id == subsidiary_id)
    if fiscal_period:
        count_stmt = count_stmt.join(FiscalPeriod).where(FiscalPeriod.period_code == fiscal_period)
        data_stmt = data_stmt.join(FiscalPeriod).where(FiscalPeriod.period_code == fiscal_period)
    if je_status:
        count_stmt = count_stmt.where(JournalEntry.status == je_status)
        data_stmt = data_stmt.where(JournalEntry.status == je_status)
    if source:
        count_stmt = count_stmt.where(JournalEntry.source == source)
        data_stmt = data_stmt.where(JournalEntry.source == source)

    total = (await db.execute(count_stmt)).scalar_one()

    data_stmt = (
        data_stmt
        .order_by(JournalEntry.entry_number.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(data_stmt)
    entries = result.scalars().unique().all()

    items = []
    for je in entries:
        total_dr = sum(float(l.debit_amount or 0) for l in je.lines)
        total_cr = sum(float(l.credit_amount or 0) for l in je.lines)
        items.append({
            "id": str(je.id),
            "entry_number": je.entry_number,
            "subsidiary_id": str(je.subsidiary_id),
            "subsidiary_name": je.subsidiary.name if je.subsidiary else None,
            "fiscal_period_id": str(je.fiscal_period_id),
            "fiscal_period_code": je.fiscal_period.period_code if je.fiscal_period else None,
            "entry_date": str(je.entry_date),
            "memo": je.memo,
            "source": je.source,
            "source_reference": je.source_reference,
            "status": je.status,
            "posted_at": je.posted_at.isoformat() if je.posted_at else None,
            "created_at": je.created_at.isoformat() if je.created_at else None,
            "total_debits": total_dr,
            "total_credits": total_cr,
            "line_count": len(je.lines),
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/journal-entries/{je_id}")
async def get_journal_entry(
    je_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.gl import JournalEntry, JournalLine

    stmt = (
        select(JournalEntry)
        .options(
            selectinload(JournalEntry.subsidiary),
            selectinload(JournalEntry.fiscal_period),
            selectinload(JournalEntry.lines).selectinload(JournalLine.account),
        )
        .where(JournalEntry.id == je_id)
    )
    result = await db.execute(stmt)
    je = result.scalar_one_or_none()
    if not je:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    lines = []
    for l in sorted(je.lines, key=lambda x: x.line_number):
        lines.append({
            "id": str(l.id),
            "line_number": l.line_number,
            "account_id": str(l.account_id),
            "account_number": l.account.account_number if l.account else None,
            "account_name": l.account.name if l.account else None,
            "debit_amount": float(l.debit_amount or 0),
            "credit_amount": float(l.credit_amount or 0),
            "memo": l.memo,
            "department_id": str(l.department_id) if l.department_id else None,
            "fund_id": str(l.fund_id) if l.fund_id else None,
            "cost_center": l.cost_center,
            "quantity": float(l.quantity) if l.quantity else None,
        })

    total_dr = sum(l["debit_amount"] for l in lines)
    total_cr = sum(l["credit_amount"] for l in lines)

    return {
        "id": str(je.id),
        "entry_number": je.entry_number,
        "subsidiary_id": str(je.subsidiary_id),
        "subsidiary_name": je.subsidiary.name if je.subsidiary else None,
        "fiscal_period_id": str(je.fiscal_period_id),
        "fiscal_period_code": je.fiscal_period.period_code if je.fiscal_period else None,
        "entry_date": str(je.entry_date),
        "memo": je.memo,
        "source": je.source,
        "source_reference": je.source_reference,
        "status": je.status,
        "posted_at": je.posted_at.isoformat() if je.posted_at else None,
        "created_at": je.created_at.isoformat() if je.created_at else None,
        "total_debits": total_dr,
        "total_credits": total_cr,
        "lines": lines,
    }


@router.post("/journal-entries", status_code=201)
async def create_journal_entry(
    body: JournalEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role("admin", "accountant")),
):
    from app.models.gl import JournalEntry, JournalLine
    from app.models.org import FiscalPeriod, Subsidiary

    # Validate subsidiary
    sub_result = await db.execute(
        select(Subsidiary).where(Subsidiary.id == body.subsidiary_id)
    )
    if not sub_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Subsidiary not found")

    # Validate lines balance
    if not body.lines or len(body.lines) < 2:
        raise HTTPException(status_code=422, detail="Journal entry must have at least 2 lines")

    total_debits = sum(l.debit_amount for l in body.lines)
    total_credits = sum(l.credit_amount for l in body.lines)

    if abs(total_debits - total_credits) > 0.005:
        raise HTTPException(
            status_code=422,
            detail=f"Debits ({total_debits}) must equal credits ({total_credits})",
        )

    # Find fiscal period for entry_date
    fp_result = await db.execute(
        select(FiscalPeriod).where(
            FiscalPeriod.start_date <= body.entry_date,
            FiscalPeriod.end_date >= body.entry_date,
            FiscalPeriod.status.in_(["open", "adjusting"]),
        )
    )
    fiscal_period = fp_result.scalar_one_or_none()
    if not fiscal_period:
        raise HTTPException(
            status_code=422,
            detail=f"No open fiscal period found for date {body.entry_date}",
        )

    # Get user_id
    user_id = user["user_id"]
    if not isinstance(user_id, uuid.UUID):
        user_id = uuid.UUID(str(user_id))

    # Create JE
    je = JournalEntry(
        subsidiary_id=body.subsidiary_id,
        fiscal_period_id=fiscal_period.id,
        entry_date=body.entry_date,
        memo=body.memo,
        source="manual",
        status="draft",
        created_by=user_id,
    )
    db.add(je)
    await db.flush()

    # Create lines
    for i, line in enumerate(body.lines, start=1):
        jl = JournalLine(
            journal_entry_id=je.id,
            line_number=i,
            account_id=line.account_id,
            debit_amount=Decimal(str(line.debit_amount)),
            credit_amount=Decimal(str(line.credit_amount)),
            memo=line.memo,
            department_id=line.department_id,
            fund_id=line.fund_id,
            cost_center=line.cost_center,
            quantity=Decimal(str(line.quantity)) if line.quantity else None,
        )
        db.add(jl)

    # Auto-post if requested
    if body.auto_post:
        je.status = "posted"
        je.posted_by = user_id
        je.posted_at = datetime.utcnow()

    await db.commit()
    await db.refresh(je)

    return {
        "id": str(je.id),
        "entry_number": je.entry_number,
        "status": je.status,
        "total_debits": float(total_debits),
        "total_credits": float(total_credits),
    }


@router.post("/journal-entries/{je_id}/post")
async def post_journal_entry(
    je_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role("admin", "accountant")),
):
    from app.models.gl import JournalEntry

    result = await db.execute(select(JournalEntry).where(JournalEntry.id == je_id))
    je = result.scalar_one_or_none()
    if not je:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if je.status != "draft":
        raise HTTPException(status_code=422, detail=f"Cannot post entry in status '{je.status}'")

    user_id = user["user_id"]
    if not isinstance(user_id, uuid.UUID):
        user_id = uuid.UUID(str(user_id))

    je.status = "posted"
    je.posted_by = user_id
    je.posted_at = datetime.utcnow()

    await db.commit()
    return {"status": "posted", "entry_number": je.entry_number}


@router.post("/journal-entries/{je_id}/reverse")
async def reverse_journal_entry(
    je_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_role("admin", "accountant")),
):
    from app.models.gl import JournalEntry, JournalLine
    from app.models.org import FiscalPeriod

    stmt = (
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(JournalEntry.id == je_id)
    )
    result = await db.execute(stmt)
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if original.status != "posted":
        raise HTTPException(status_code=422, detail="Can only reverse posted entries")

    user_id = user["user_id"]
    if not isinstance(user_id, uuid.UUID):
        user_id = uuid.UUID(str(user_id))

    # Create reversal JE
    reversal = JournalEntry(
        subsidiary_id=original.subsidiary_id,
        fiscal_period_id=original.fiscal_period_id,
        entry_date=date.today(),
        memo=f"Reversal of JE #{original.entry_number}: {original.memo or ''}",
        source=original.source,
        source_reference=f"reversal:{original.id}",
        status="posted",
        posted_by=user_id,
        posted_at=datetime.utcnow(),
        created_by=user_id,
    )
    db.add(reversal)
    await db.flush()

    # Swap debits and credits
    for i, line in enumerate(original.lines, start=1):
        rl = JournalLine(
            journal_entry_id=reversal.id,
            line_number=i,
            account_id=line.account_id,
            debit_amount=line.credit_amount,  # swapped
            credit_amount=line.debit_amount,  # swapped
            memo=f"Reversal: {line.memo or ''}",
            department_id=line.department_id,
            fund_id=line.fund_id,
            cost_center=line.cost_center,
            quantity=line.quantity,
        )
        db.add(rl)

    # Mark original as reversed
    original.status = "reversed"
    original.reversed_by_je_id = reversal.id

    await db.commit()
    await db.refresh(reversal)

    return {
        "original_entry_number": original.entry_number,
        "reversal_id": str(reversal.id),
        "reversal_entry_number": reversal.entry_number,
        "status": "reversed",
    }


# ---------------------------------------------------------------------------
# TRIAL BALANCE
# ---------------------------------------------------------------------------

@router.get("/trial-balance")
async def get_trial_balance(
    fiscal_period: str = Query(..., description="Period code like 2026-02"),
    subsidiary_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    from app.models.gl import Account, JournalEntry, JournalLine
    from app.models.org import FiscalPeriod

    # Find fiscal period
    fp_result = await db.execute(
        select(FiscalPeriod).where(FiscalPeriod.period_code == fiscal_period)
    )
    fp = fp_result.scalar_one_or_none()
    if not fp:
        raise HTTPException(status_code=404, detail=f"Fiscal period '{fiscal_period}' not found")

    # Build query: sum debits and credits per account from posted JEs in this period
    stmt = (
        select(
            Account.account_number,
            Account.name,
            Account.account_type,
            func.coalesce(func.sum(JournalLine.debit_amount), 0).label("total_debits"),
            func.coalesce(func.sum(JournalLine.credit_amount), 0).label("total_credits"),
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            JournalEntry.status == "posted",
            JournalEntry.fiscal_period_id == fp.id,
        )
    )

    if subsidiary_id:
        stmt = stmt.where(JournalEntry.subsidiary_id == subsidiary_id)

    stmt = stmt.group_by(
        Account.account_number, Account.name, Account.account_type
    ).order_by(Account.account_number)

    result = await db.execute(stmt)
    rows = result.all()

    items = []
    grand_debits = 0.0
    grand_credits = 0.0

    for row in rows:
        dr = float(row.total_debits)
        cr = float(row.total_credits)
        items.append(TrialBalanceItem(
            account_number=row.account_number,
            account_name=row.name,
            account_type=row.account_type,
            debit_balance=dr,
            credit_balance=cr,
        ))
        grand_debits += dr
        grand_credits += cr

    return TrialBalanceResponse(
        fiscal_period=fiscal_period,
        subsidiary_id=subsidiary_id,
        items=items,
        total_debits=grand_debits,
        total_credits=grand_credits,
    )


# ---------------------------------------------------------------------------
# FUNDS
# ---------------------------------------------------------------------------

@router.get("/funds")
async def list_funds(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """List all funds."""
    from app.models.fund import Fund

    result = await db.execute(
        select(Fund).where(Fund.is_active == True).order_by(Fund.code)
    )
    funds = result.scalars().all()

    return {
        "items": [
            {
                "id": str(f.id),
                "code": f.code,
                "name": f.name,
                "fund_type": f.fund_type,
                "description": f.description,
                "is_active": f.is_active,
            }
            for f in funds
        ],
        "total": len(funds),
    }
