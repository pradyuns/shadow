from datetime import datetime, timedelta, timezone
from typing import Any, cast

import bcrypt
from jose import JWTError, jwt

from app.config import settings


# bcrypt hash with auto-generated salt
def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


# constant-time comparison via bcrypt
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# shared jwt minting logic — all token types differ only in type label and ttl
def _create_token(data: dict[str, Any], token_type: str, expires_in: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_in
    to_encode.update({"exp": expire, "type": token_type})
    encoded = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return cast(str, encoded)


def create_access_token(data: dict[str, Any]) -> str:
    return _create_token(data, "access", timedelta(minutes=settings.jwt_access_token_expire_minutes))


def create_refresh_token(data: dict[str, Any]) -> str:
    return _create_token(data, "refresh", timedelta(days=settings.jwt_refresh_token_expire_days))


def create_email_verification_token(data: dict[str, Any]) -> str:
    return _create_token(data, "email_verify", timedelta(hours=settings.email_verification_token_expire_hours))


# returns payload dict or none if signature/expiry is invalid
def decode_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return cast(dict[str, Any], payload)
    except JWTError:
        return None
