"""Financial statement reports — P&L, Balance Sheet, Fund Balances."""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import case, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user

router = APIRouter(prefix="/api/reports", tags=["reports"])


# ---------------------------------------------------------------------------
# Statement of Activities (P&L) — Non-profit version of Income Statement
# ---------------------------------------------------------------------------

@router.get("/statement-of-activities")
async def statement_of_activities(
    fiscal_period: str = Query(...),
    subsidiary_id: uuid.UUID | None = Query(None),
    fund_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Generate Statement of Activities (P&L) for a fiscal period."""
    from app.models.gl import Account, JournalEntry, JournalLine
    from app.models.org import FiscalPeriod

    fp_result = await db.execute(
        select(FiscalPeriod).where(FiscalPeriod.period_code == fiscal_period)
    )
    fp = fp_result.scalar_one_or_none()
    if not fp:
        raise HTTPException(status_code=404, detail="Fiscal period not found")

    # Get totals by account for revenue and expense accounts
    stmt = (
        select(
            Account.account_number,
            Account.name,
            Account.account_type,
            Account.normal_balance,
            func.coalesce(func.sum(JournalLine.debit_amount), 0).label("total_debits"),
            func.coalesce(func.sum(JournalLine.credit_amount), 0).label("total_credits"),
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            JournalEntry.status == "posted",
            JournalEntry.fiscal_period_id == fp.id,
            Account.account_type.in_(["revenue", "expense"]),
        )
    )

    if subsidiary_id:
        stmt = stmt.where(JournalEntry.subsidiary_id == subsidiary_id)
    if fund_id:
        stmt = stmt.where(JournalLine.fund_id == fund_id)

    stmt = stmt.group_by(
        Account.account_number, Account.name, Account.account_type, Account.normal_balance
    ).order_by(Account.account_number)

    result = await db.execute(stmt)
    rows = result.all()

    revenue_items = []
    expense_items = []
    total_revenue = 0.0
    total_expenses = 0.0

    for row in rows:
        # For revenue (credit-normal): balance = credits - debits
        # For expense (debit-normal): balance = debits - credits
        if row.normal_balance == "credit":
            balance = float(row.total_credits) - float(row.total_debits)
        else:
            balance = float(row.total_debits) - float(row.total_credits)

        item = {
            "account_number": row.account_number,
            "account_name": row.name,
            "amount": abs(balance),
        }

        if row.account_type == "revenue":
            revenue_items.append(item)
            total_revenue += abs(balance)
        else:
            expense_items.append(item)
            total_expenses += abs(balance)

    return {
        "title": "Statement of Activities",
        "fiscal_period": fiscal_period,
        "subsidiary_id": str(subsidiary_id) if subsidiary_id else None,
        "revenue": {
            "items": revenue_items,
            "total": total_revenue,
        },
        "expenses": {
            "items": expense_items,
            "total": total_expenses,
        },
        "change_in_net_assets": total_revenue - total_expenses,
    }


# ---------------------------------------------------------------------------
# Statement of Financial Position (Balance Sheet)
# ---------------------------------------------------------------------------

@router.get("/statement-of-financial-position")
async def statement_of_financial_position(
    as_of_period: str = Query(...),
    subsidiary_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Generate Balance Sheet as of end of a fiscal period.

    Includes ALL posted JEs up to and including the given period.
    """
    from app.models.gl import Account, JournalEntry, JournalLine
    from app.models.org import FiscalPeriod

    # Get all periods up to and including the target
    fp_result = await db.execute(
        select(FiscalPeriod).where(FiscalPeriod.period_code == as_of_period)
    )
    target_fp = fp_result.scalar_one_or_none()
    if not target_fp:
        raise HTTPException(status_code=404, detail="Fiscal period not found")

    # All periods up to target end date
    all_fp = await db.execute(
        select(FiscalPeriod.id).where(FiscalPeriod.end_date <= target_fp.end_date)
    )
    period_ids = [r[0] for r in all_fp.all()]

    # Sum all postings for balance sheet accounts (asset, liability, equity)
    stmt = (
        select(
            Account.account_number,
            Account.name,
            Account.account_type,
            Account.normal_balance,
            func.coalesce(func.sum(JournalLine.debit_amount), 0).label("total_debits"),
            func.coalesce(func.sum(JournalLine.credit_amount), 0).label("total_credits"),
        )
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            JournalEntry.status == "posted",
            JournalEntry.fiscal_period_id.in_(period_ids),
        )
    )

    if subsidiary_id:
        stmt = stmt.where(JournalEntry.subsidiary_id == subsidiary_id)

    stmt = stmt.group_by(
        Account.account_number, Account.name, Account.account_type, Account.normal_balance
    ).order_by(Account.account_number)

    result = await db.execute(stmt)
    rows = result.all()

    assets = []
    liabilities = []
    equity = []
    total_assets = 0.0
    total_liabilities = 0.0
    total_equity = 0.0

    for row in rows:
        if row.normal_balance == "debit":
            balance = float(row.total_debits) - float(row.total_credits)
        else:
            balance = float(row.total_credits) - float(row.total_debits)

        item = {
            "account_number": row.account_number,
            "account_name": row.name,
            "amount": balance,
        }

        if row.account_type == "asset":
            assets.append(item)
            total_assets += balance
        elif row.account_type == "liability":
            liabilities.append(item)
            total_liabilities += balance
        elif row.account_type == "equity":
            equity.append(item)
            total_equity += balance

    # Include net income in equity
    # (Revenue - Expenses from all periods up to target)
    income_stmt = (
        select(
            func.coalesce(func.sum(
                case(
                    (Account.account_type == "revenue", JournalLine.credit_amount - JournalLine.debit_amount),
                    else_=0,
                )
            ), 0).label("revenue"),
            func.coalesce(func.sum(
                case(
                    (Account.account_type == "expense", JournalLine.debit_amount - JournalLine.credit_amount),
                    else_=0,
                )
            ), 0).label("expenses"),
        )
        .select_from(Account)
        .join(JournalLine, JournalLine.account_id == Account.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            JournalEntry.status == "posted",
            JournalEntry.fiscal_period_id.in_(period_ids),
            Account.account_type.in_(["revenue", "expense"]),
        )
    )
    if subsidiary_id:
        income_stmt = income_stmt.where(JournalEntry.subsidiary_id == subsidiary_id)

    income_result = await db.execute(income_stmt)
    income_row = income_result.one()
    net_income = float(income_row.revenue) - float(income_row.expenses)

    total_equity += net_income

    return {
        "title": "Statement of Financial Position",
        "as_of_period": as_of_period,
        "subsidiary_id": str(subsidiary_id) if subsidiary_id else None,
        "assets": {"items": assets, "total": total_assets},
        "liabilities": {"items": liabilities, "total": total_liabilities},
        "net_assets": {
            "items": equity,
            "retained_earnings": net_income,
            "total": total_equity,
        },
        "total_liabilities_and_net_assets": total_liabilities + total_equity,
        "is_balanced": abs(total_assets - (total_liabilities + total_equity)) < 0.01,
    }


# ---------------------------------------------------------------------------
# Fund Balance Report
# ---------------------------------------------------------------------------

@router.get("/fund-balances")
async def fund_balances(
    fiscal_period: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    """Show balance by fund across all accounts."""
    from app.models.gl import JournalEntry, JournalLine
    from app.models.fund import Fund
    from app.models.org import FiscalPeriod

    fp_result = await db.execute(
        select(FiscalPeriod).where(FiscalPeriod.period_code == fiscal_period)
    )
    fp = fp_result.scalar_one_or_none()
    if not fp:
        raise HTTPException(status_code=404, detail="Fiscal period not found")

    # All periods up to target
    all_fp = await db.execute(
        select(FiscalPeriod.id).where(FiscalPeriod.end_date <= fp.end_date)
    )
    period_ids = [r[0] for r in all_fp.all()]

    stmt = (
        select(
            Fund.code,
            Fund.name,
            Fund.fund_type,
            func.coalesce(func.sum(JournalLine.credit_amount - JournalLine.debit_amount), 0).label("net_balance"),
        )
        .join(JournalLine, JournalLine.fund_id == Fund.id)
        .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
        .where(
            JournalEntry.status == "posted",
            JournalEntry.fiscal_period_id.in_(period_ids),
        )
        .group_by(Fund.code, Fund.name, Fund.fund_type)
        .order_by(Fund.code)
    )

    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for row in rows:
        items.append({
            "fund_code": row.code,
            "fund_name": row.name,
            "fund_type": row.fund_type,
            "balance": float(row.net_balance),
        })

    # Also get funds with zero balance
    all_funds = await db.execute(select(Fund).where(Fund.is_active == True).order_by(Fund.code))
    fund_codes_with_balance = {r["fund_code"] for r in items}
    for f in all_funds.scalars().all():
        if f.code not in fund_codes_with_balance:
            items.append({
                "fund_code": f.code,
                "fund_name": f.name,
                "fund_type": f.fund_type,
                "balance": 0.0,
            })

    items.sort(key=lambda x: x["fund_code"])

    return {
        "fiscal_period": fiscal_period,
        "items": items,
        "total": sum(i["balance"] for i in items),
    }
