"""Refresh rotation and logout against a real database, not mocked queries."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.refresh_session import RefreshSession
from app.models.user import User
from app.services.auth_service import refresh_tokens, revoke_session, start_session


@pytest.mark.asyncio
async def test_refresh_rotation_and_logout_prevent_replay():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(User.__table__.create)
        await connection.run_sync(RefreshSession.__table__.create)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as db:
            user = User(id=uuid.uuid4(), email="user@example.com", password_hash="hash", full_name="User")
            db.add(user)
            await db.commit()
            initial = await start_session(db, user)
            rotated = await refresh_tokens(db, initial["refresh_token"])
            assert rotated is not None
            assert await refresh_tokens(db, initial["refresh_token"]) is None
            # Logout remains effective even if it races with a rotation and has the old cookie.
            await revoke_session(db, initial["refresh_token"])
            assert await refresh_tokens(db, rotated["refresh_token"]) is None
    finally:
        await engine.dispose()
