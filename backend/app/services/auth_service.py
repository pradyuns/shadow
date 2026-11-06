import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.refresh_session import RefreshSession
from app.models.user import User
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


async def register_user(db: AsyncSession, email: str, password: str, full_name: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        raise ValueError("Email already registered")

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def create_tokens(user: User, session_id: uuid.UUID, token_id: uuid.UUID) -> dict[str, Any]:
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id), "sid": str(session_id), "jti": str(token_id)})
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }


def _refresh_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)


async def start_session(db: AsyncSession, user: User) -> dict[str, Any]:
    session_id, token_id = uuid.uuid4(), uuid.uuid4()
    await db.execute(
        delete(RefreshSession).where(
            RefreshSession.user_id == user.id, RefreshSession.expires_at <= datetime.now(timezone.utc)
        )
    )
    db.add(RefreshSession(id=session_id, user_id=user.id, token_id=token_id, expires_at=_refresh_expiry()))
    await db.commit()
    return create_tokens(user, session_id, token_id)


def _refresh_claims(token: str) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID] | None:
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        return None
    try:
        return uuid.UUID(payload["sub"]), uuid.UUID(payload["sid"]), uuid.UUID(payload["jti"])
    except (KeyError, ValueError, TypeError, AttributeError):
        return None


async def refresh_tokens(db: AsyncSession, refresh_token_str: str) -> dict[str, Any] | None:
    claims = _refresh_claims(refresh_token_str)
    if claims is None:
        return None
    user_id, session_id, old_token_id = claims
    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if not user:
        return None
    new_token_id = uuid.uuid4()
    result = await db.execute(
        update(RefreshSession)
        .where(
            RefreshSession.id == session_id,
            RefreshSession.user_id == user_id,
            RefreshSession.token_id == old_token_id,
            RefreshSession.expires_at > datetime.now(timezone.utc),
        )
        .values(token_id=new_token_id, expires_at=_refresh_expiry())
        .returning(RefreshSession.id)
    )
    if result.scalar_one_or_none() is None:
        await db.rollback()
        return None
    await db.commit()
    return create_tokens(user, session_id, new_token_id)


async def revoke_session(db: AsyncSession, token: str | None) -> None:
    claims = _refresh_claims(token) if token else None
    if claims is not None:
        user_id, session_id, _ = claims
        await db.execute(
            delete(RefreshSession).where(RefreshSession.id == session_id, RefreshSession.user_id == user_id)
        )
        await db.commit()
