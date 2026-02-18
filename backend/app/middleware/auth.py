"""Authentication and authorization middleware for KAILASA ERP.

Provides:
- Password hashing (bcrypt)
- JWT creation / validation
- ``get_current_user()`` dependency
- ``require_role()`` (backward-compatible) and ``require_permission()``
- Subsidiary data-scoping helpers
- Audit-log helper
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.rbac import GLOBAL_SCOPE_ROLES, get_role_permissions

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    """Compare a plain-text password against a bcrypt hash."""
    return _pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    """Return the bcrypt hash of a plain-text password."""
    return _pwd_context.hash(plain)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def create_access_token(data: dict[str, Any]) -> str:
    """Create a signed JWT containing *sub* (username), *role*, and *exp*."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    to_encode.update({"exp": expire})

    # Ensure user_id is serialised as a string so the JWT payload stays
    # JSON-compatible (UUIDs are not natively serialisable).
    if "user_id" in to_encode and not isinstance(to_encode["user_id"], str):
        to_encode["user_id"] = str(to_encode["user_id"])

    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# OAuth2 scheme (tells Swagger UI where the login endpoint is)
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login/form")

# ---------------------------------------------------------------------------
# Current-user dependency
# ---------------------------------------------------------------------------


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Decode the JWT, look up the user in the ``users`` table, and return a
    dict describing the authenticated user.

    Raises ``HTTPException(401)`` when the token is invalid or the user cannot
    be found.

    Also stores the user dict on ``request.state._audit_user`` so the
    read-access audit middleware can correlate requests to users.
    """
    # Import here to avoid circular imports at module level
    from app.models.user import User

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Query the users table
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    user: User | None = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    user_dict = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "display_name": user.display_name,
        "email": user.email,
        "subsidiary_id": str(user.subsidiary_id) if user.subsidiary_id else None,
    }

    # Store on request for read-access audit middleware
    request.state._audit_user = user_dict

    return user_dict


# ---------------------------------------------------------------------------
# Permission resolution (role base + DB overrides)
# ---------------------------------------------------------------------------


async def resolve_permissions(
    user: dict[str, Any],
    db: AsyncSession,
) -> set[str]:
    """Compute the effective permission set for a user.

    1. Start with role base permissions from ``ROLE_PERMISSIONS``.
    2. Apply per-user overrides from ``user_permission_overrides`` table
       (grants add, revokes remove), skipping expired overrides.
    """
    from app.models.permission import UserPermissionOverride

    base = get_role_permissions(user["role"]).copy()

    # Fetch active overrides
    user_id = user["user_id"]
    if not isinstance(user_id, uuid.UUID):
        user_id = uuid.UUID(str(user_id))

    stmt = select(UserPermissionOverride).where(
        UserPermissionOverride.user_id == user_id,
    )
    result = await db.execute(stmt)
    overrides = result.scalars().all()

    now = datetime.now(timezone.utc)
    for ov in overrides:
        # Skip expired overrides
        if ov.expires_at and ov.expires_at.replace(tzinfo=timezone.utc) < now:
            continue
        if ov.granted:
            base.add(ov.permission)
        else:
            base.discard(ov.permission)

    return base


# ---------------------------------------------------------------------------
# Permission-checking dependency factory (new — granular)
# ---------------------------------------------------------------------------


def require_permission(*permissions: str):
    """Return a FastAPI dependency that ensures the authenticated user has
    ALL of the specified permissions (role-based + overrides).

    Usage::

        @router.post("/accounts", status_code=201)
        async def create_account(
            body: AccountCreate,
            db: AsyncSession = Depends(get_db),
            user: dict = Depends(require_permission("gl.accounts.create")),
        ):
            ...
    """
    required = set(permissions)

    async def _check_permission(
        current_user: dict[str, Any] = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> dict[str, Any]:
        effective = await resolve_permissions(current_user, db)
        missing = required - effective
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permissions: {', '.join(sorted(missing))}.",
            )
        return current_user

    return _check_permission


# ---------------------------------------------------------------------------
# Role-checking dependency factory (backward-compatible)
# ---------------------------------------------------------------------------

# Map old role names → new role names for backward compatibility in tests
_ROLE_COMPAT: dict[str, str] = {
    "admin": "system_admin",
    "accountant": "senior_accountant",
}


def require_role(*roles: str):
    """Return a FastAPI dependency that ensures the authenticated user holds one
    of the specified *roles*.

    Supports both old role names (admin, accountant) and new ones
    (system_admin, senior_accountant, etc.) for backward compatibility.

    Usage::

        @router.get("/admin-only")
        async def admin_view(user=Depends(require_role("admin"))):
            ...
    """
    # Expand old role names to include new equivalents
    allowed = set()
    for r in roles:
        allowed.add(r)
        # Also accept the new name if an old name was passed
        if r in _ROLE_COMPAT:
            allowed.add(_ROLE_COMPAT[r])
        # Also accept the old name if a new name was passed
        for old, new in _ROLE_COMPAT.items():
            if r == new:
                allowed.add(old)

    async def _check_role(
        current_user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        if current_user["role"] not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user['role']}' is not permitted. "
                f"Required: {', '.join(sorted(allowed))}.",
            )
        return current_user

    return _check_role


# ---------------------------------------------------------------------------
# Data scoping — subsidiary-level isolation
# ---------------------------------------------------------------------------


def get_subsidiary_scope(user: dict[str, Any]) -> uuid.UUID | None:
    """Return the subsidiary UUID to filter by, or ``None`` for global access.

    Roles in ``GLOBAL_SCOPE_ROLES`` (system_admin, controller, auditor) see
    all subsidiaries.  Other roles are scoped to their assigned subsidiary.
    """
    if user["role"] in GLOBAL_SCOPE_ROLES:
        return None
    sub_id = user.get("subsidiary_id")
    if sub_id is None:
        return None
    return uuid.UUID(sub_id) if isinstance(sub_id, str) else sub_id


def apply_subsidiary_filter(stmt, user: dict[str, Any], subsidiary_column):
    """Apply subsidiary filtering to a SQLAlchemy ``select()`` statement.

    If the user has global scope, the statement is returned unmodified.
    Otherwise a ``.where(subsidiary_column == <user's subsidiary>)`` is added.
    """
    scope = get_subsidiary_scope(user)
    if scope is not None:
        stmt = stmt.where(subsidiary_column == scope)
    return stmt


# ---------------------------------------------------------------------------
# Triple audit writer singleton
# ---------------------------------------------------------------------------

_triple_writer: "TripleAuditWriter | None" = None


def _get_triple_writer():
    """Lazy-initialise the singleton TripleAuditWriter."""
    global _triple_writer
    if _triple_writer is None:
        from app.services.audit_service import TripleAuditWriter

        _triple_writer = TripleAuditWriter(
            base_path=settings.AUDIT_STORAGE_PATH,
            system_name="erp",
        )
    return _triple_writer


# ---------------------------------------------------------------------------
# Audit-log helper
# ---------------------------------------------------------------------------


async def write_audit_log(
    db: AsyncSession,
    user: dict[str, Any] | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """Write to PostgreSQL, then fire-and-forget to JSONL + SQLite."""
    from app.models.permission import AuditLog
    from app.services.audit_service import AuditEvent, classify_action

    category = classify_action(action)

    user_id = None
    username = None
    if user:
        uid = user.get("user_id")
        if uid:
            user_id = uid if isinstance(uid, uuid.UUID) else uuid.UUID(str(uid))
        username = user.get("username")

    # ---- Primary: PostgreSQL (existing behaviour) ----
    entry = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        event_category=category.value,
    )
    db.add(entry)
    await db.flush()

    # ---- Secondary: JSONL + SQLite (non-blocking) ----
    event = AuditEvent(
        id=entry.id,
        timestamp=datetime.now(timezone.utc),
        category=category,
        user_id=str(user_id) if user_id else None,
        username=username,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        system_name="erp",
    )
    _get_triple_writer().fire_and_forget(event)
