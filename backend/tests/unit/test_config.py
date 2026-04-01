import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_rejects_default_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(jwt_secret_key="change-this-to-a-random-secret-key")


def test_settings_rejects_empty_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(jwt_secret_key="   ")


def test_settings_accepts_non_default_jwt_secret():
    config = Settings(jwt_secret_key="test-secret-key-for-testing-only")
    assert config.jwt_secret_key == "test-secret-key-for-testing-only"
