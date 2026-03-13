import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.db.postgres import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import UserRead
from app.services.auth_service import authenticate_user, create_tokens, refresh_tokens, register_user
from app.utils.security import decode_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await register_user(db, body.email, body.password, body.full_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    from workers.tasks.email_verification import send_verification_email

    send_verification_email.delay(str(user.id))

    return user


@router.post("/login", response_model=TokenPair)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return create_tokens(user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    tokens = await refresh_tokens(db, body.refresh_token)
    if not tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")
    return tokens


@router.get("/verify-email")
async def verify_email(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    payload = decode_token(token)
    if payload is None or payload.get("type") != "email_verify":
        return RedirectResponse(f"{settings.frontend_url}/login?verify_error=invalid")

    user_id = payload.get("sub")
    if not user_id:
        return RedirectResponse(f"{settings.frontend_url}/login?verify_error=invalid")

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        return RedirectResponse(f"{settings.frontend_url}/login?verify_error=invalid")

    result = await db.execute(select(User).where(User.id == uid, User.is_active == True))
    user = result.scalar_one_or_none()

    if not user:
        return RedirectResponse(f"{settings.frontend_url}/login?verify_error=not_found")

    if not user.is_email_verified:
        user.is_email_verified = True
        user.email_verified_at = datetime.now(timezone.utc)
        await db.commit()

    return RedirectResponse(f"{settings.frontend_url}/login?verified=true")


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
async def resend_verification(user: User = Depends(get_current_user)):
    if user.is_email_verified:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already verified")

    from workers.tasks.email_verification import send_verification_email

    send_verification_email.delay(str(user.id))

    return {"status": "accepted", "message": "Verification email sent"}
