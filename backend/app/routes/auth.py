"""Authentication routes."""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_user

from jose import jwt
from passlib.context import CryptContext

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    from app.models.user import User

    stmt = select(User).where(User.username == body.username, User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not pwd_context.verify(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = _create_token(user)
    return TokenResponse(
        access_token=token,
        user={
            "id": str(user.id),
            "username": user.username,
            "display_name": user.display_name,
            "email": user.email,
            "role": user.role,
            "subsidiary_id": str(user.subsidiary_id) if user.subsidiary_id else None,
        },
    )


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return {
        "username": user["username"],
        "role": user["role"],
        "user_id": str(user["user_id"]),
        "subsidiary_id": user.get("subsidiary_id"),
        "display_name": user.get("display_name", user["username"]),
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
