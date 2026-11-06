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


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        ("postgresql://user:pass@db/test", "postgresql+psycopg2://user:pass@db/test"),
        ("postgresql+psycopg://user:pass@db/test", "postgresql+psycopg://user:pass@db/test"),
        ("postgresql+psycopg2://user:pass@db/test", "postgresql+psycopg2://user:pass@db/test"),
    ],
)
def test_sync_postgres_driver_is_explicit(configured, expected):
    config = Settings(jwt_secret_key="test-secret-key-for-testing-only", database_url_sync=configured)
    assert config.database_url_sync == expected


def test_default_sync_postgres_driver_is_psycopg2(monkeypatch):
    monkeypatch.delenv("DATABASE_URL_SYNC", raising=False)
    config = Settings(jwt_secret_key="test-secret-key-for-testing-only", _env_file=None)
    assert config.database_url_sync.startswith("postgresql+psycopg2://")
