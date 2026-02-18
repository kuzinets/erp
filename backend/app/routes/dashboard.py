"""Dashboard routes — KPIs and overview data."""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, require_permission, apply_subsidiary_filter

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("reports.dashboard.view")),
):
    """Main dashboard with KPIs."""
    from app.models.gl import Account, JournalEntry, JournalLine
    from app.models.org import FiscalPeriod, Subsidiary
    from app.models.fund import Fund
    from app.models.subsystem import SubsystemConfig

    # Find current fiscal period
    today = date.today()
    fp_result = await db.execute(
        select(FiscalPeriod).where(
            FiscalPeriod.start_date <= today,
            FiscalPeriod.end_date >= today,
        )
    )
    current_period = fp_result.scalar_one_or_none()
    period_code = current_period.period_code if current_period else None
    period_id = current_period.id if current_period else None

    # Subsidiary scoping
    from app.middleware.auth import get_subsidiary_scope
    sub_scope = get_subsidiary_scope(_user)

    # KPIs for current period
    total_revenue = 0.0
    total_expenses = 0.0
    je_count = 0

    if period_id:
        # Revenue (credit-normal accounts)
        rev_stmt = (
            select(
                func.coalesce(
                    func.sum(JournalLine.credit_amount - JournalLine.debit_amount), 0
                )
            )
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .join(Account, Account.id == JournalLine.account_id)
            .where(
                JournalEntry.status == "posted",
                JournalEntry.fiscal_period_id == period_id,
                Account.account_type == "revenue",
            )
        )
        if sub_scope is not None:
            rev_stmt = rev_stmt.where(JournalEntry.subsidiary_id == sub_scope)
        total_revenue = float((await db.execute(rev_stmt)).scalar_one())

        # Expenses (debit-normal accounts)
        exp_stmt = (
            select(
                func.coalesce(
                    func.sum(JournalLine.debit_amount - JournalLine.credit_amount), 0
                )
            )
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .join(Account, Account.id == JournalLine.account_id)
            .where(
                JournalEntry.status == "posted",
                JournalEntry.fiscal_period_id == period_id,
                Account.account_type == "expense",
            )
        )
        if sub_scope is not None:
            exp_stmt = exp_stmt.where(JournalEntry.subsidiary_id == sub_scope)
        total_expenses = float((await db.execute(exp_stmt)).scalar_one())

        # JE count
        je_stmt = select(func.count(JournalEntry.id)).where(
            JournalEntry.fiscal_period_id == period_id,
            JournalEntry.status == "posted",
        )
        if sub_scope is not None:
            je_stmt = je_stmt.where(JournalEntry.subsidiary_id == sub_scope)
        je_count = (await db.execute(je_stmt)).scalar_one()

    # Subsidiary count
    sub_count_stmt = select(func.count(Subsidiary.id)).where(Subsidiary.is_active == True)
    if sub_scope is not None:
        sub_count_stmt = sub_count_stmt.where(Subsidiary.id == sub_scope)
    sub_count = (await db.execute(sub_count_stmt)).scalar_one()

    # Fund count
    fund_count = (await db.execute(
        select(func.count(Fund.id)).where(Fund.is_active == True)
    )).scalar_one()

    # Connected systems
    sys_result = await db.execute(
        select(SubsystemConfig).where(SubsystemConfig.is_active == True)
    )
    systems = sys_result.scalars().all()
    connected_systems = [
        {
            "name": s.name,
            "system_type": s.system_type,
            "last_sync_at": s.last_sync_at.isoformat() if s.last_sync_at else None,
        }
        for s in systems
    ]

    # Recent JEs (last 10)
    recent_jes = []
    je_recent_stmt = (
        select(JournalEntry)
        .where(JournalEntry.status == "posted")
        .order_by(JournalEntry.created_at.desc())
        .limit(10)
    )
    if sub_scope is not None:
        je_recent_stmt = je_recent_stmt.where(JournalEntry.subsidiary_id == sub_scope)
    je_result = await db.execute(je_recent_stmt)
    for je in je_result.scalars().all():
        recent_jes.append({
            "id": str(je.id),
            "entry_number": je.entry_number,
            "entry_date": str(je.entry_date),
            "memo": je.memo,
            "source": je.source,
            "status": je.status,
        })

    # Account count
    acct_count = (await db.execute(
        select(func.count(Account.id)).where(Account.is_active == True)
    )).scalar_one()

    return {
        "current_period": period_code,
        "kpis": {
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "net_income": total_revenue - total_expenses,
            "journal_entries": je_count,
            "subsidiaries": sub_count,
            "funds": fund_count,
            "accounts": acct_count,
        },
        "connected_systems": connected_systems,
        "recent_journal_entries": recent_jes,
    }
