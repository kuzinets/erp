"""Subsystem integration routes -- manage connected systems and sync."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import get_current_user, require_permission, write_audit_log

router = APIRouter(prefix="/api/subsystems", tags=["subsystems"])


class SubsystemConfigCreate(BaseModel):
    name: str
    system_type: str
    base_url: str
    api_username: str | None = None
    api_password: str | None = None
    subsidiary_id: uuid.UUID | None = None
    sync_frequency_minutes: int = 1440


class SubsystemConfigUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    api_username: str | None = None
    is_active: bool | None = None
    sync_frequency_minutes: int | None = None


class AccountMappingCreate(BaseModel):
    source_account_code: str
    target_account_id: uuid.UUID
    source_posting_type: str | None = None
    description: str | None = None


# ---------------------------------------------------------------------------
# SUBSYSTEM CONFIGS
# ---------------------------------------------------------------------------

@router.get("")
async def list_subsystems(
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("subsystems.view")),
):
    from app.models.subsystem import SubsystemConfig

    stmt = (
        select(SubsystemConfig)
        .options(selectinload(SubsystemConfig.subsidiary))
        .order_by(SubsystemConfig.name)
    )
    result = await db.execute(stmt)
    configs = result.scalars().all()

    items = []
    for c in configs:
        items.append({
            "id": str(c.id),
            "name": c.name,
            "system_type": c.system_type,
            "base_url": c.base_url,
            "api_username": c.api_username,
            "subsidiary_id": str(c.subsidiary_id) if c.subsidiary_id else None,
            "subsidiary_name": c.subsidiary.name if c.subsidiary else None,
            "sync_frequency_minutes": c.sync_frequency_minutes,
            "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
            "is_active": c.is_active,
        })

    return {"items": items, "total": len(items)}


@router.get("/{config_id}")
async def get_subsystem(
    config_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("subsystems.view")),
):
    from app.models.subsystem import SubsystemConfig, SubsystemAccountMapping

    result = await db.execute(
        select(SubsystemConfig)
        .options(
            selectinload(SubsystemConfig.subsidiary),
            selectinload(SubsystemConfig.account_mappings).selectinload(SubsystemAccountMapping.target_account),
        )
        .where(SubsystemConfig.id == config_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Subsystem config not found")

    mappings = []
    for m in c.account_mappings:
        mappings.append({
            "id": str(m.id),
            "source_account_code": m.source_account_code,
            "target_account_id": str(m.target_account_id),
            "target_account_number": m.target_account.account_number if m.target_account else None,
            "target_account_name": m.target_account.name if m.target_account else None,
            "source_posting_type": m.source_posting_type,
            "description": m.description,
            "is_active": m.is_active,
        })

    return {
        "id": str(c.id),
        "name": c.name,
        "system_type": c.system_type,
        "base_url": c.base_url,
        "api_username": c.api_username,
        "subsidiary_id": str(c.subsidiary_id) if c.subsidiary_id else None,
        "subsidiary_name": c.subsidiary.name if c.subsidiary else None,
        "sync_frequency_minutes": c.sync_frequency_minutes,
        "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
        "is_active": c.is_active,
        "account_mappings": mappings,
    }


@router.post("", status_code=201)
async def create_subsystem(
    body: SubsystemConfigCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("subsystems.create")),
):
    from app.models.subsystem import SubsystemConfig
    from passlib.context import CryptContext

    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

    config = SubsystemConfig(
        name=body.name,
        system_type=body.system_type,
        base_url=body.base_url,
        api_username=body.api_username,
        api_password_hash=pwd.hash(body.api_password) if body.api_password else None,
        subsidiary_id=body.subsidiary_id,
        sync_frequency_minutes=body.sync_frequency_minutes,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    await write_audit_log(db, _user, "subsystem.create", "subsystem_config", str(config.id), {"name": body.name, "system_type": body.system_type})
    return {"id": str(config.id), "name": config.name}


@router.put("/{config_id}")
async def update_subsystem(
    config_id: uuid.UUID,
    body: SubsystemConfigUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("subsystems.update")),
):
    from app.models.subsystem import SubsystemConfig

    result = await db.execute(
        select(SubsystemConfig).where(SubsystemConfig.id == config_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Subsystem config not found")

    for field in ["name", "base_url", "api_username", "is_active", "sync_frequency_minutes"]:
        val = getattr(body, field, None)
        if val is not None:
            setattr(config, field, val)

    await db.commit()
    await write_audit_log(db, _user, "subsystem.update", "subsystem_config", str(config_id), body.dict(exclude_unset=True))
    return {"status": "updated"}


# ---------------------------------------------------------------------------
# ACCOUNT MAPPINGS
# ---------------------------------------------------------------------------

@router.get("/{config_id}/mappings")
async def list_account_mappings(
    config_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("subsystems.view")),
):
    from app.models.subsystem import SubsystemAccountMapping

    stmt = (
        select(SubsystemAccountMapping)
        .options(selectinload(SubsystemAccountMapping.target_account))
        .where(SubsystemAccountMapping.subsystem_config_id == config_id)
        .order_by(SubsystemAccountMapping.source_account_code)
    )
    result = await db.execute(stmt)
    mappings = result.scalars().all()

    return {
        "items": [
            {
                "id": str(m.id),
                "source_account_code": m.source_account_code,
                "target_account_id": str(m.target_account_id),
                "target_account_number": m.target_account.account_number if m.target_account else None,
                "target_account_name": m.target_account.name if m.target_account else None,
                "source_posting_type": m.source_posting_type,
                "description": m.description,
                "is_active": m.is_active,
            }
            for m in mappings
        ]
    }


@router.post("/{config_id}/mappings", status_code=201)
async def create_account_mapping(
    config_id: uuid.UUID,
    body: AccountMappingCreate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("subsystems.create")),
):
    from app.models.subsystem import SubsystemAccountMapping

    mapping = SubsystemAccountMapping(
        subsystem_config_id=config_id,
        source_account_code=body.source_account_code,
        target_account_id=body.target_account_id,
        source_posting_type=body.source_posting_type,
        description=body.description,
    )
    db.add(mapping)
    await db.commit()
    await db.refresh(mapping)
    await write_audit_log(db, _user, "subsystem.mapping.create", "subsystem_account_mapping", str(mapping.id), {"source_account_code": body.source_account_code, "config_id": str(config_id)})
    return {"id": str(mapping.id), "source_account_code": mapping.source_account_code}


# ---------------------------------------------------------------------------
# SYNC OPERATIONS
# ---------------------------------------------------------------------------

@router.post("/{config_id}/sync")
async def trigger_sync(
    config_id: uuid.UUID,
    fiscal_period: str = Query(..., description="Period to sync, e.g. 2026-02"),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission("subsystems.sync")),
):
    """Trigger a sync from a connected subsystem for a given fiscal period."""
    from app.services.sync_service import SyncService

    service = SyncService(db)
    result = await service.sync_from_subsystem(config_id, fiscal_period, user)
    await write_audit_log(db, user, "subsystem.sync", "subsystem_config", str(config_id), {"fiscal_period": fiscal_period})
    return result


@router.get("/{config_id}/sync-logs")
async def list_sync_logs(
    config_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_permission("subsystems.view")),
):
    from app.models.subsystem import SyncLog
    from sqlalchemy import func

    count_stmt = select(func.count(SyncLog.id)).where(SyncLog.subsystem_config_id == config_id)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(SyncLog)
        .where(SyncLog.subsystem_config_id == config_id)
        .order_by(SyncLog.started_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return {
        "items": [
            {
                "id": str(l.id),
                "started_at": l.started_at.isoformat() if l.started_at else None,
                "completed_at": l.completed_at.isoformat() if l.completed_at else None,
                "status": l.status,
                "fiscal_period_synced": l.fiscal_period_synced,
                "postings_imported": l.postings_imported,
                "journal_entries_created": l.journal_entries_created,
                "error_message": l.error_message,
            }
            for l in logs
        ],
        "total": total,
    }
