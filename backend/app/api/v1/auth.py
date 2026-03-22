import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.db.postgres import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, SessionResponse
from app.schemas.user import UserRead
from app.services.auth_service import authenticate_user, create_tokens, refresh_tokens, register_user
from app.utils.security import decode_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookies(response: Response, tokens: dict) -> None:
    response.set_cookie(
        key=settings.auth_access_cookie_name,
        value=tokens["access_token"],
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        domain=settings.auth_cookie_domain or None,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=tokens["refresh_token"],
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        domain=settings.auth_cookie_domain or None,
        max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
        path="/",
    )


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie(
        key=settings.auth_access_cookie_name,
        domain=settings.auth_cookie_domain or None,
        path="/",
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )
    response.delete_cookie(
        key=settings.auth_refresh_cookie_name,
        domain=settings.auth_cookie_domain or None,
        path="/",
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await register_user(db, body.email, body.password, body.full_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    from workers.tasks.email_verification import send_verification_email

    send_verification_email.delay(str(user.id))

    return user


@router.post("/login", response_model=SessionResponse)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    tokens = create_tokens(user)
    _set_session_cookies(response, tokens)
    return {"status": "authenticated", "expires_in": tokens["expires_in"]}


@router.post("/refresh", response_model=SessionResponse)
async def refresh(
    request: Request,
    response: Response,
    body: RefreshRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    refresh_token = request.cookies.get(settings.auth_refresh_cookie_name) or (body.refresh_token if body else None)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    tokens = await refresh_tokens(db, refresh_token)
    if not tokens:
        _clear_session_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")
    _set_session_cookies(response, tokens)
    return {"status": "authenticated", "expires_in": tokens["expires_in"]}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    _clear_session_cookies(response)


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
