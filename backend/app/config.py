from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "Competitor Intelligence Monitor"
    app_version: str = "0.1.0"
    log_level: str = "info"
    log_format: str = "console"  # "json" for production, "console" for development
    enable_docs: bool = True
    enable_metrics: bool = True

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://compmon:changeme@postgres:5432/compmon"
    database_url_sync: str = "postgresql://compmon:changeme@postgres:5432/compmon"

    # MongoDB
    mongodb_url: str = "mongodb://compmon:changeme@mongodb:27017/compmon?authSource=admin"
    mongodb_database: str = "compmon"

    # Redis
    redis_url: str = "redis://redis:6379/0"
    redis_result_url: str = "redis://redis:6379/1"
    redis_cache_url: str = "redis://redis:6379/2"

    # JWT
    jwt_secret_key: str = "change-this-to-a-random-secret-key"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"
    auth_access_cookie_name: str = "shadow_access_token"
    auth_refresh_cookie_name: str = "shadow_refresh_token"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    auth_cookie_domain: str | None = None

    # Anthropic
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens_budget: int = 4000
    claude_rate_limit_per_minute: int = 20

    # SendGrid
    sendgrid_api_key: str = ""
    sendgrid_from_email: str = "alerts@yourcompany.com"

    # Slack
    slack_webhook_url: str = ""

    # Email verification
    frontend_url: str = "http://localhost:3000"
    email_verification_token_expire_hours: int = 24

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # Firecrawl (fallback scraper for bot-protected sites)
    firecrawl_api_key: str = ""

    # Scraping
    default_check_interval_hours: int = 6
    max_monitors_per_user: int = 50
    scrape_batch_size: int = 20
    scrape_timeout_seconds: int = 60
    scrape_hard_timeout_seconds: int = 90

    # Cleanup
    snapshot_ttl_days: int = 90
    diff_ttl_days: int = 180
    analysis_ttl_days: int = 365
    deleted_monitor_retention_days: int = 30


settings = Settings()
