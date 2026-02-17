from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

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
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Decode the JWT, look up the user in the ``users`` table, and return a
    dict describing the authenticated user.

    Raises ``HTTPException(401)`` when the token is invalid or the user cannot
    be found.
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

    return {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "display_name": user.display_name,
        "email": user.email,
        "subsidiary_id": str(user.subsidiary_id) if user.subsidiary_id else None,
    }


# ---------------------------------------------------------------------------
# Role-checking dependency factory
# ---------------------------------------------------------------------------


def require_role(*roles: str):
    """Return a FastAPI dependency that ensures the authenticated user holds one
    of the specified *roles*.

    Valid roles: admin, accountant, program_manager, viewer

    Usage::

        @router.get("/admin-only")
        async def admin_view(user=Depends(require_role("admin"))):
            ...

        @router.get("/staff-or-admin")
        async def staff_view(user=Depends(require_role("admin", "accountant"))):
            ...
    """
    allowed = set(roles)

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
