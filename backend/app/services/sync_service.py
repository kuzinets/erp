"""Sync service — pulls GL postings from connected subsystems (Library, etc.)."""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, date
from decimal import Decimal

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings


class SyncService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_from_subsystem(
        self,
        config_id: uuid.UUID,
        fiscal_period: str,
        user: dict,
    ) -> dict:
        """
        Sync GL postings from a subsystem for a given fiscal period.

        1. Login to subsystem API
        2. Pull ERP export for the period
        3. Map source account codes to ERP accounts
        4. Create summary journal entry (grouped by account)
        5. Log sync result
        """
        from app.models.subsystem import SubsystemConfig, SubsystemAccountMapping, SyncLog
        from app.models.gl import JournalEntry, JournalLine, Account
        from app.models.org import FiscalPeriod

        # Load config
        result = await self.db.execute(
            select(SubsystemConfig).where(SubsystemConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if not config:
            raise ValueError("Subsystem config not found")

        if not config.is_active:
            raise ValueError("Subsystem is disabled")

        # Create sync log
        sync_log = SyncLog(
            subsystem_config_id=config_id,
            fiscal_period_synced=fiscal_period,
            status="running",
        )
        self.db.add(sync_log)
        await self.db.flush()

        try:
            # Step 1: Login to subsystem
            base_url = config.base_url.rstrip("/")
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Login
                login_resp = await client.post(
                    f"{base_url}/api/auth/login",
                    json={
                        "username": config.api_username or "dmitry",
                        "password": "admin123",  # In production, use encrypted password
                    },
                )
                if login_resp.status_code != 200:
                    raise Exception(f"Login failed: {login_resp.status_code} {login_resp.text[:200]}")

                token = login_resp.json().get("access_token")

                # Step 2: Pull ERP export
                export_resp = await client.get(
                    f"{base_url}/api/finance/erp-export",
                    params={"fiscal_period": fiscal_period},
                    headers={"Authorization": f"Bearer {token}"},
                )
                if export_resp.status_code != 200:
                    raise Exception(f"ERP export failed: {export_resp.status_code} {export_resp.text[:200]}")

                export_data = export_resp.json()

            postings = export_data.get("items", [])
            posting_count = len(postings)

            if posting_count == 0:
                sync_log.status = "success"
                sync_log.completed_at = datetime.utcnow()
                sync_log.postings_imported = 0
                sync_log.journal_entries_created = 0
                config.last_sync_at = datetime.utcnow()
                await self.db.commit()
                return {
                    "status": "success",
                    "message": "No postings to import",
                    "postings_imported": 0,
                    "journal_entries_created": 0,
                }

            # Step 3: Load account mappings
            mapping_result = await self.db.execute(
                select(SubsystemAccountMapping)
                .where(
                    SubsystemAccountMapping.subsystem_config_id == config_id,
                    SubsystemAccountMapping.is_active == True,
                )
            )
            mappings = mapping_result.scalars().all()
            mapping_dict = {}
            for m in mappings:
                key = m.source_account_code
                mapping_dict[key] = m.target_account_id

            # Step 4: Group postings by account code and aggregate
            aggregated = defaultdict(lambda: {"debit": Decimal("0"), "credit": Decimal("0"), "count": 0})

            for p in postings:
                acct_code = p.get("account_code", "")
                amount = Decimal(str(p.get("amount", "0")))
                posting_type = p.get("posting_type", "debit")

                if acct_code not in mapping_dict:
                    # Try direct account lookup by number
                    acct_result = await self.db.execute(
                        select(Account).where(Account.account_number == acct_code)
                    )
                    acct = acct_result.scalar_one_or_none()
                    if acct:
                        mapping_dict[acct_code] = acct.id
                    else:
                        continue  # Skip unmapped accounts

                if posting_type == "debit":
                    aggregated[acct_code]["debit"] += abs(amount)
                else:
                    aggregated[acct_code]["credit"] += abs(amount)
                aggregated[acct_code]["count"] += 1

            # Step 5: Find fiscal period
            fp_result = await self.db.execute(
                select(FiscalPeriod).where(FiscalPeriod.period_code == fiscal_period)
            )
            fp = fp_result.scalar_one_or_none()
            if not fp:
                raise Exception(f"Fiscal period {fiscal_period} not found in ERP")

            # Check for existing sync JE (idempotent)
            source_ref = f"{config.system_type}:{fiscal_period}"
            existing = await self.db.execute(
                select(JournalEntry).where(
                    JournalEntry.source_reference == source_ref,
                    JournalEntry.subsidiary_id == config.subsidiary_id,
                    JournalEntry.source == config.system_type,
                )
            )
            existing_je = existing.scalar_one_or_none()

            if existing_je:
                # Update: reverse old and create new
                if existing_je.status == "posted":
                    existing_je.status = "reversed"

            # Get user_id
            user_id = user["user_id"]
            if not isinstance(user_id, uuid.UUID):
                user_id = uuid.UUID(str(user_id))

            # Create summary JE
            total_units = sum(v["count"] for v in aggregated.values())
            je = JournalEntry(
                subsidiary_id=config.subsidiary_id,
                fiscal_period_id=fp.id,
                entry_date=fp.end_date,
                memo=f"{config.name} — {fiscal_period} ({total_units} postings imported)",
                source=config.system_type,
                source_reference=source_ref,
                status="posted",
                posted_by=user_id,
                posted_at=datetime.utcnow(),
                created_by=user_id,
            )
            self.db.add(je)
            await self.db.flush()

            # Create lines
            line_num = 0
            for acct_code, amounts in sorted(aggregated.items()):
                target_acct_id = mapping_dict.get(acct_code)
                if not target_acct_id:
                    continue

                if amounts["debit"] > 0:
                    line_num += 1
                    self.db.add(JournalLine(
                        journal_entry_id=je.id,
                        line_number=line_num,
                        account_id=target_acct_id,
                        debit_amount=amounts["debit"],
                        credit_amount=Decimal("0"),
                        memo=f"{config.name}: {acct_code} ({amounts['count']} postings)",
                        cost_center=config.subsidiary.code if config.subsidiary else None,
                    ))

                if amounts["credit"] > 0:
                    line_num += 1
                    self.db.add(JournalLine(
                        journal_entry_id=je.id,
                        line_number=line_num,
                        account_id=target_acct_id,
                        debit_amount=Decimal("0"),
                        credit_amount=amounts["credit"],
                        memo=f"{config.name}: {acct_code} ({amounts['count']} postings)",
                        cost_center=config.subsidiary.code if config.subsidiary else None,
                    ))

            # Finalize
            sync_log.status = "success"
            sync_log.completed_at = datetime.utcnow()
            sync_log.postings_imported = posting_count
            sync_log.journal_entries_created = 1
            config.last_sync_at = datetime.utcnow()

            await self.db.commit()

            return {
                "status": "success",
                "postings_imported": posting_count,
                "journal_entries_created": 1,
                "journal_entry_id": str(je.id),
                "entry_number": je.entry_number,
            }

        except Exception as e:
            sync_log.status = "failed"
            sync_log.completed_at = datetime.utcnow()
            sync_log.error_message = str(e)[:500]
            await self.db.commit()
            return {
                "status": "failed",
                "error": str(e)[:500],
                "postings_imported": 0,
                "journal_entries_created": 0,
            }
