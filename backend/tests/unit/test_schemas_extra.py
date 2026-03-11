"""Tests for additional schemas (analysis, common)."""

from datetime import datetime, timezone

import pytest

from app.schemas.analysis import AnalysisRead
from app.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    PaginatedResponse,
    ReadinessResponse,
)


class TestAnalysisRead:
    def test_valid_analysis(self):
        analysis = AnalysisRead(
            id="abc123",
            diff_id="diff-1",
            monitor_id="mon-1",
            significance_level="critical",
            summary="Major pricing change",
            categories=["pricing"],
            claude_model="claude-sonnet-4-20250514",
            prompt_tokens=100,
            completion_tokens=50,
            total_cost_usd=0.001,
            needs_review=False,
            created_at=datetime.now(timezone.utc),
        )
        assert analysis.significance_level == "critical"
        assert analysis.categories == ["pricing"]

    def test_nullable_fields(self):
        analysis = AnalysisRead(
            id="abc123",
            diff_id="diff-1",
            monitor_id="mon-1",
            significance_level="low",
            summary="Minor update",
            categories=[],
            claude_model=None,
            prompt_tokens=None,
            completion_tokens=None,
            total_cost_usd=None,
            needs_review=True,
            created_at=datetime.now(timezone.utc),
        )
        assert analysis.claude_model is None
        assert analysis.needs_review is True


class TestPaginatedResponse:
    def test_paginated_response(self):
        resp = PaginatedResponse[str](
            items=["a", "b", "c"],
            total=10,
            page=1,
            per_page=3,
            pages=4,
        )
        assert resp.total == 10
        assert len(resp.items) == 3
        assert resp.pages == 4


class TestErrorResponse:
    def test_error_response(self):
        resp = ErrorResponse(error=ErrorDetail(code="NOT_FOUND", message="Resource not found"))
        assert resp.error.code == "NOT_FOUND"
        assert resp.error.details is None

    def test_error_response_with_details(self):
        resp = ErrorResponse(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="Invalid input",
                details={"field": "email", "reason": "invalid format"},
            )
        )
        assert resp.error.details["field"] == "email"


class TestHealthResponse:
    def test_health_response(self):
        resp = HealthResponse(status="ok", timestamp=datetime.now(timezone.utc))
        assert resp.status == "ok"


class TestReadinessResponse:
    def test_readiness_response(self):
        resp = ReadinessResponse(
            status="ready",
            postgres="ok",
            mongodb="ok",
            redis="ok",
        )
        assert resp.status == "ready"
        assert resp.postgres == "ok"
