"""Tests for security utilities (password hashing, JWT tokens)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    """Test bcrypt password operations."""

    def test_hash_password_returns_string(self):
        hashed = hash_password("mypassword123")
        assert isinstance(hashed, str)

    def test_hash_password_not_plaintext(self):
        password = "mypassword123"
        hashed = hash_password(password)
        assert hashed != password

    def test_hash_starts_with_bcrypt_prefix(self):
        hashed = hash_password("test")
        assert hashed.startswith("$2b$")

    def test_different_passwords_different_hashes(self):
        hash1 = hash_password("password1")
        hash2 = hash_password("password2")
        assert hash1 != hash2

    def test_same_password_different_hashes(self):
        # bcrypt uses random salt, so same password gives different hashes
        hash1 = hash_password("samepassword")
        hash2 = hash_password("samepassword")
        assert hash1 != hash2

    def test_verify_correct_password(self):
        password = "correct_password"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_verify_invalid_hash_returns_false(self):
        assert verify_password("password", "not-a-valid-hash") is False

    def test_verify_empty_password(self):
        hashed = hash_password("realpassword")
        assert verify_password("", hashed) is False


class TestJWTTokens:
    """Test JWT token creation and decoding."""

    def test_create_access_token(self):
        token = create_access_token({"sub": "user-123"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        token = create_refresh_token({"sub": "user-123"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_access_and_refresh_tokens_differ(self):
        data = {"sub": "user-123"}
        access = create_access_token(data)
        refresh = create_refresh_token(data)
        assert access != refresh

    def test_decode_access_token(self):
        data = {"sub": "user-123"}
        token = create_access_token(data)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_decode_refresh_token(self):
        data = {"sub": "user-456"}
        token = create_refresh_token(data)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-456"
        assert payload["type"] == "refresh"

    def test_decode_token_has_expiry(self):
        token = create_access_token({"sub": "user-123"})
        payload = decode_token(token)
        assert "exp" in payload

    def test_decode_invalid_token_returns_none(self):
        assert decode_token("invalid.token.here") is None

    def test_decode_empty_token_returns_none(self):
        assert decode_token("") is None

    def test_decode_tampered_token_returns_none(self):
        token = create_access_token({"sub": "user-123"})
        # Tamper with the token
        tampered = token[:-5] + "XXXXX"
        assert decode_token(tampered) is None

    def test_token_preserves_custom_data(self):
        data = {"sub": "user-123", "email": "test@test.com"}
        token = create_access_token(data)
        payload = decode_token(token)
        assert payload["email"] == "test@test.com"
