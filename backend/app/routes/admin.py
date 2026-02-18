"""Administration routes --- User management, permission overrides, audit log."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import (
    hash_password,
    require_permission,
    resolve_permissions,
    write_audit_log,
)
from app.rbac import (
    ALL_PERMISSIONS,
    GLOBAL_SCOPE_ROLES,
    ROLE_PERMISSIONS,
    VALID_ROLES,
    permission_description,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str
    email: str | None = None
    role: str
    subsidiary_id: uuid.UUID | None = None


class UserUpdate(BaseModel):
    display_name: str | None = None
    email: str | None = None
    role: str | None = None
    subsidiary_id: uuid.UUID | None = None
    is_active: bool | None = None


class PermissionOverrideCreate(BaseModel):
    permission: str
    granted: bool
    reason: str | None = None
    expires_at: datetime | None = None


# ---------------------------------------------------------------------------
# USER MANAGEMENT
# ---------------------------------------------------------------------------


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission("admin.users.view")),
):
    """List all users."""
    from app.models.user import User

    stmt = select(User).order_by(User.username)
    result = await db.execute(stmt)
    users = result.scalars().all()

    items = []
    for u in users:
        item = {
            "id": str(u.id),
            "username": u.username,
            "display_name": u.display_name,
            "email": u.email,
            "role": u.role,
            "subsidiary_id": str(u.subsidiary_id) if u.subsidiary_id else None,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        # Include subsidiary name if the relationship is loaded
        if u.subsidiary is not None:
            item["subsidiary_name"] = u.subsidiary.name
        else:
            item["subsidiary_name"] = None
        items.append(item)

    return {"items": items, "total": len(items)}


@router.get("/users/{user_id}")
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission("admin.users.view")),
):
    """Get a single user with effective permissions and overrides."""
    from app.models.permission import UserPermissionOverride
    from app.models.user import User

    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")

    # Build a user dict for resolve_permissions
    user_dict = {
        "user_id": u.id,
        "username": u.username,
        "role": u.role,
        "subsidiary_id": str(u.subsidiary_id) if u.subsidiary_id else None,
    }
    effective = await resolve_permissions(user_dict, db)

    # Fetch overrides
    stmt = select(UserPermissionOverride).where(
        UserPermissionOverride.user_id == user_id
    )
    ov_result = await db.execute(stmt)
    overrides = ov_result.scalars().all()

    override_list = [
        {
            "id": str(ov.id),
            "permission": ov.permission,
            "granted": ov.granted,
            "reason": ov.reason,
            "granted_by": str(ov.granted_by) if ov.granted_by else None,
            "expires_at": ov.expires_at.isoformat() if ov.expires_at else None,
            "created_at": ov.created_at.isoformat() if ov.created_at else None,
        }
        for ov in overrides
    ]

    return {
        "id": str(u.id),
        "username": u.username,
        "display_name": u.display_name,
        "email": u.email,
        "role": u.role,
        "subsidiary_id": str(u.subsidiary_id) if u.subsidiary_id else None,
        "subsidiary_name": u.subsidiary.name if u.subsidiary else None,
        "is_active": u.is_active,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "effective_permissions": sorted(effective),
        "overrides": override_list,
    }


@router.post("/users", status_code=201)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission("admin.users.create")),
):
    """Create a new user."""
    from app.models.user import User

    # Validate role
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid role '{body.role}'. Valid roles: {', '.join(VALID_ROLES)}",
        )

    # Check for duplicate username
    existing = await db.execute(
        select(User).where(User.username == body.username)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username already exists")

    new_user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        email=body.email,
        role=body.role,
        subsidiary_id=body.subsidiary_id,
    )
    db.add(new_user)
    await db.flush()

    await write_audit_log(
        db,
        user,
        action="user.create",
        resource_type="user",
        resource_id=str(new_user.id),
        details={"username": body.username, "role": body.role},
    )

    await db.commit()
    await db.refresh(new_user)

    return {
        "id": str(new_user.id),
        "username": new_user.username,
        "role": new_user.role,
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission("admin.users.update")),
):
    """Update an existing user."""
    from app.models.user import User

    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    changes = {}

    if body.role is not None:
        if body.role not in VALID_ROLES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid role '{body.role}'. Valid roles: {', '.join(VALID_ROLES)}",
            )
        changes["role"] = body.role
        target.role = body.role

    if body.display_name is not None:
        changes["display_name"] = body.display_name
        target.display_name = body.display_name

    if body.email is not None:
        changes["email"] = body.email
        target.email = body.email

    if body.subsidiary_id is not None:
        changes["subsidiary_id"] = str(body.subsidiary_id)
        target.subsidiary_id = body.subsidiary_id

    if body.is_active is not None:
        changes["is_active"] = body.is_active
        target.is_active = body.is_active

    await write_audit_log(
        db,
        user,
        action="user.update",
        resource_type="user",
        resource_id=str(user_id),
        details=changes,
    )

    await db.commit()
    return {"status": "updated"}


# ---------------------------------------------------------------------------
# PERMISSION OVERRIDES
# ---------------------------------------------------------------------------


@router.post("/users/{user_id}/permissions", status_code=201)
async def create_permission_override(
    user_id: uuid.UUID,
    body: PermissionOverrideCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission("admin.users.manage_permissions")),
):
    """Grant or revoke a permission override for a user."""
    from app.models.permission import UserPermissionOverride
    from app.models.user import User

    # Verify target user exists
    target_result = await db.execute(select(User).where(User.id == user_id))
    if not target_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")

    # Validate permission string
    if body.permission not in ALL_PERMISSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown permission '{body.permission}'.",
        )

    # Upsert: check if override already exists for this user + permission
    stmt = select(UserPermissionOverride).where(
        UserPermissionOverride.user_id == user_id,
        UserPermissionOverride.permission == body.permission,
    )
    existing_result = await db.execute(stmt)
    existing = existing_result.scalar_one_or_none()

    granter_id = user.get("user_id")
    if granter_id and not isinstance(granter_id, uuid.UUID):
        granter_id = uuid.UUID(str(granter_id))

    if existing:
        # Update existing override
        existing.granted = body.granted
        existing.reason = body.reason
        existing.expires_at = body.expires_at
        existing.granted_by = granter_id
        override = existing
    else:
        # Create new override
        override = UserPermissionOverride(
            user_id=user_id,
            permission=body.permission,
            granted=body.granted,
            reason=body.reason,
            granted_by=granter_id,
            expires_at=body.expires_at,
        )
        db.add(override)

    await db.flush()

    action_word = "grant" if body.granted else "revoke"
    await write_audit_log(
        db,
        user,
        action=f"permission.{action_word}",
        resource_type="user_permission_override",
        resource_id=str(override.id),
        details={
            "target_user_id": str(user_id),
            "permission": body.permission,
            "granted": body.granted,
            "reason": body.reason,
        },
    )

    await db.commit()

    return {
        "id": str(override.id),
        "permission": override.permission,
        "granted": override.granted,
    }


@router.delete("/users/{user_id}/permissions/{permission}")
async def delete_permission_override(
    user_id: uuid.UUID,
    permission: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission("admin.users.manage_permissions")),
):
    """Remove a permission override for a user."""
    from app.models.permission import UserPermissionOverride

    stmt = select(UserPermissionOverride).where(
        UserPermissionOverride.user_id == user_id,
        UserPermissionOverride.permission == permission,
    )
    result = await db.execute(stmt)
    override = result.scalar_one_or_none()

    if not override:
        raise HTTPException(status_code=404, detail="Permission override not found")

    override_id = str(override.id)
    await db.delete(override)

    await write_audit_log(
        db,
        user,
        action="permission.delete",
        resource_type="user_permission_override",
        resource_id=override_id,
        details={
            "target_user_id": str(user_id),
            "permission": permission,
        },
    )

    await db.commit()
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# ROLES
# ---------------------------------------------------------------------------


@router.get("/roles")
async def list_roles(
    user: dict = Depends(require_permission("admin.users.view")),
):
    """List all roles with their default permissions."""
    roles = []
    for role_code in sorted(ROLE_PERMISSIONS.keys()):
        perms = sorted(ROLE_PERMISSIONS[role_code])
        scope = "global" if role_code in GLOBAL_SCOPE_ROLES else "subsidiary"
        roles.append({
            "code": role_code,
            "permissions": perms,
            "scope": scope,
        })

    return {"roles": roles}


# ---------------------------------------------------------------------------
# AUDIT LOG
# ---------------------------------------------------------------------------


@router.get("/audit-log")
async def list_audit_log(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    action: str | None = Query(None),
    username: str | None = Query(None),
    resource_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_permission("admin.audit_log.view")),
):
    """Paginated audit trail."""
    from app.models.permission import AuditLog

    # Build base query
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)

    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    if username:
        stmt = stmt.where(AuditLog.username == username)
        count_stmt = count_stmt.where(AuditLog.username == username)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
        count_stmt = count_stmt.where(AuditLog.resource_type == resource_type)

    # Total count
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    # Paginate
    offset = (page - 1) * page_size
    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(stmt)
    entries = result.scalars().all()

    items = [
        {
            "id": str(e.id),
            "user_id": str(e.user_id) if e.user_id else None,
            "username": e.username,
            "action": e.action,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "details": e.details,
            "ip_address": e.ip_address,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
