"""Tests for Pydantic schema validation."""

import uuid

import pytest
from pydantic import ValidationError

from app.schemas.alert import AlertDetail, AlertRead, Severity
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, SessionResponse
from app.schemas.monitor import MonitorCreate, MonitorRead, MonitorUpdate, PageType
from app.schemas.notification import Channel, NotificationSettingRead, NotificationSettingUpdate
from workers.classifier.schemas import (
    ChangeCategory,
    ClassificationResult,
    SignificanceLevel,
)


class TestAuthSchemas:
    """Test auth request/response schemas."""

    def test_register_valid(self):
        req = RegisterRequest(email="test@example.com", password="password123", full_name="Test User")
        assert req.email == "test@example.com"

    def test_register_invalid_email(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="not-an-email", password="password123", full_name="Test")

    def test_register_short_password(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="test@example.com", password="short", full_name="Test")

    def test_register_long_password(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="test@example.com", password="a" * 129, full_name="Test")

    def test_register_empty_name(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="test@example.com", password="password123", full_name="")

    def test_login_valid(self):
        req = LoginRequest(email="test@example.com", password="pass")
        assert req.email == "test@example.com"

    def test_refresh_valid(self):
        req = RefreshRequest(refresh_token="some-token")
        assert req.refresh_token == "some-token"

    def test_session_response(self):
        session = SessionResponse(status="authenticated", expires_in=1800)
        assert session.status == "authenticated"
        assert session.expires_in == 1800


class TestMonitorSchemas:
    """Test monitor schemas."""

    def test_create_valid(self):
        mc = MonitorCreate(
            url="https://example.com/pricing",
            name="Example Pricing",
            page_type=PageType.pricing,
        )
        assert str(mc.url) == "https://example.com/pricing"

    def test_create_invalid_url(self):
        with pytest.raises(ValidationError):
            MonitorCreate(url="not-a-url", name="Test", page_type=PageType.pricing)

    def test_create_with_all_fields(self):
        mc = MonitorCreate(
            url="https://example.com",
            name="Full Monitor",
            competitor_name="Example",
            page_type=PageType.changelog,
            render_js=True,
            check_interval_hours=12,
            css_selector=".content",
            noise_patterns=[r"\d{4}"],
        )
        assert mc.render_js is True
        assert mc.check_interval_hours == 12

    def test_create_invalid_interval_too_high(self):
        with pytest.raises(ValidationError):
            MonitorCreate(
                url="https://example.com",
                name="Test",
                page_type=PageType.pricing,
                check_interval_hours=200,
            )

    def test_create_invalid_interval_too_low(self):
        with pytest.raises(ValidationError):
            MonitorCreate(
                url="https://example.com",
                name="Test",
                page_type=PageType.pricing,
                check_interval_hours=0,
            )

    def test_update_partial(self):
        mu = MonitorUpdate(name="New Name")
        assert mu.name == "New Name"
        assert mu.page_type is None

    def test_page_type_enum(self):
        assert PageType.pricing.value == "pricing"
        assert PageType.changelog.value == "changelog"
        assert PageType.homepage.value == "homepage"
        assert PageType.jobs.value == "jobs"
        assert PageType.blog.value == "blog"
        assert PageType.docs.value == "docs"

    def test_create_invalid_page_type(self):
        with pytest.raises(ValidationError):
            MonitorCreate(
                url="https://example.com",
                name="Test",
                page_type="invalid_type",
            )


class TestAlertSchemas:
    """Test alert schemas."""

    def test_severity_enum(self):
        assert Severity.critical.value == "critical"
        assert Severity.high.value == "high"
        assert Severity.medium.value == "medium"
        assert Severity.low.value == "low"

    def test_alert_read(self):
        alert = AlertRead(
            id=uuid.uuid4(),
            monitor_id=uuid.uuid4(),
            severity="high",
            summary="Test alert",
            categories=["pricing_change"],
            is_acknowledged=False,
            notified_at=None,
            created_at="2024-01-01T00:00:00Z",
        )
        assert alert.severity == "high"


class TestNotificationSchemas:
    """Test notification schemas."""

    def test_channel_enum(self):
        assert Channel.slack.value == "slack"
        assert Channel.email.value == "email"

    def test_setting_update_defaults(self):
        su = NotificationSettingUpdate()
        assert su.is_enabled is True
        assert su.min_severity == "medium"
        assert su.digest_mode is False

    def test_setting_update_digest_hour_range(self):
        su = NotificationSettingUpdate(digest_hour_utc=23)
        assert su.digest_hour_utc == 23

    def test_setting_update_invalid_digest_hour(self):
        with pytest.raises(ValidationError):
            NotificationSettingUpdate(digest_hour_utc=24)

    def test_setting_update_negative_digest_hour(self):
        with pytest.raises(ValidationError):
            NotificationSettingUpdate(digest_hour_utc=-1)


class TestClassificationSchemas:
    """Test Claude classification schemas."""

    def test_significance_levels(self):
        for level in ["critical", "high", "medium", "low", "noise"]:
            assert SignificanceLevel(level).value == level

    def test_change_categories(self):
        expected = [
            "pricing_change",
            "feature_launch",
            "feature_removal",
            "hiring_signal",
            "messaging_change",
            "partnership",
            "technical_change",
            "other",
        ]
        for cat in expected:
            assert ChangeCategory(cat).value == cat

    def test_classification_result_valid(self):
        result = ClassificationResult(
            significance_level=SignificanceLevel.high,
            summary="Test summary",
            categories=[ChangeCategory.pricing_change],
        )
        assert result.significance_level == SignificanceLevel.high

    def test_classification_result_invalid_level(self):
        with pytest.raises(ValidationError):
            ClassificationResult(
                significance_level="invalid",
                summary="Test",
                categories=["other"],
            )

    def test_classification_result_empty_categories(self):
        with pytest.raises(ValidationError):
            ClassificationResult(
                significance_level=SignificanceLevel.medium,
                summary="Test",
                categories=[],
            )

    def test_classification_result_long_summary(self):
        with pytest.raises(ValidationError):
            ClassificationResult(
                significance_level=SignificanceLevel.medium,
                summary="x" * 1001,
                categories=[ChangeCategory.other],
            )
