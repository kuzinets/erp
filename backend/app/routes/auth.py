"""Authentication routes."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_user, write_audit_log
from app.services.audit_service import AuditEvent, AuditEventCategory

from jose import jwt
from passlib.context import CryptContext

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _log_failed_auth(username: str, request: Request) -> None:
    """Fire-and-forget a SYSTEM audit event for a failed login attempt."""
    from app.middleware.auth import _get_triple_writer

    event = AuditEvent(
        id=uuid4(),
        timestamp=datetime.now(timezone.utc),
        category=AuditEventCategory.SYSTEM,
        user_id=None,
        username=username,
        action="auth.failed",
        resource_type="auth",
        resource_id=None,
        details={"reason": "invalid_credentials"},
        ip_address=request.client.host if request.client else None,
        system_name="erp",
    )
    _get_triple_writer().fire_and_forget(event)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserOut(BaseModel):
    id: str
    username: str
    display_name: str
    email: str | None
    role: str
    subsidiary_id: str | None


def _create_token(user_row) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    payload = {
        "sub": user_row.username,
        "role": user_row.role,
        "user_id": str(user_row.id),
        "subsidiary_id": str(user_row.subsidiary_id) if user_row.subsidiary_id else None,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    from app.models.user import User

    stmt = select(User).where(User.username == body.username, User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(body.password, user.password_hash):
        # Log failed authentication attempt
        _log_failed_auth(body.username, request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = _create_token(user)

    # Resolve effective permissions to include in login response
    from app.middleware.auth import resolve_permissions
    from app.rbac import GLOBAL_SCOPE_ROLES

    user_dict = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "subsidiary_id": str(user.subsidiary_id) if user.subsidiary_id else None,
    }
    permissions = await resolve_permissions(user_dict, db)
    scope = "global" if user.role in GLOBAL_SCOPE_ROLES else "subsidiary"

    # Audit log the login
    await write_audit_log(
        db,
        user_dict,
        "auth.login",
        resource_type="user",
        resource_id=str(user.id),
        details={"username": user.username},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return TokenResponse(
        access_token=token,
        user={
            "id": str(user.id),
            "username": user.username,
            "display_name": user.display_name,
            "email": user.email,
            "role": user.role,
            "subsidiary_id": str(user.subsidiary_id) if user.subsidiary_id else None,
            "permissions": sorted(permissions),
            "scope": scope,
        },
    )


@router.get("/me")
async def get_me(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.middleware.auth import resolve_permissions
    from app.rbac import GLOBAL_SCOPE_ROLES

    permissions = await resolve_permissions(user, db)
    scope = "global" if user["role"] in GLOBAL_SCOPE_ROLES else "subsidiary"

    return {
        "username": user["username"],
        "role": user["role"],
        "user_id": str(user["user_id"]),
        "subsidiary_id": user.get("subsidiary_id"),
        "display_name": user.get("display_name", user["username"]),
        "email": user.get("email"),
        "permissions": sorted(permissions),
        "scope": scope,
    }


@router.post("/refresh")
async def refresh_token(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    from app.models.user import User

    stmt = select(User).where(User.username == user["username"], User.is_active == True)
    result = await db.execute(stmt)
    user_row = result.scalar_one_or_none()
    if not user_row:
        raise HTTPException(status_code=401, detail="User not found")

    token = _create_token(user_row)
    return {"access_token": token, "token_type": "bearer"}
