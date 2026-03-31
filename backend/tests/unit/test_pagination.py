"""Tests for pagination utility."""

import pytest

from app.utils.pagination import PaginationParams


class TestPaginationParams:
    """Test pagination parameter calculations."""

    def test_default_values(self):
        params = PaginationParams()
        assert params.page == 1
        assert params.per_page == 20
        assert params.offset == 0

    def test_limit_alias_overrides_per_page(self):
        params = PaginationParams(page=2, per_page=20, limit=5)
        assert params.page == 2
        assert params.per_page == 5
        assert params.offset == 5

    def test_custom_page(self):
        params = PaginationParams(page=3, per_page=20)
        assert params.offset == 40

    def test_offset_calculation(self):
        params = PaginationParams(page=5, per_page=10)
        assert params.offset == 40

    def test_page_1_offset_is_zero(self):
        params = PaginationParams(page=1, per_page=50)
        assert params.offset == 0


class TestPaginate:
    """Test paginate method."""

    def test_basic_pagination(self):
        params = PaginationParams(page=1, per_page=10)
        items = list(range(10))
        result = params.paginate(items, total=25)
        assert result["items"] == items
        assert result["total"] == 25
        assert result["page"] == 1
        assert result["per_page"] == 10
        assert result["pages"] == 3

    def test_last_partial_page(self):
        params = PaginationParams(page=1, per_page=10)
        result = params.paginate([], total=15)
        assert result["pages"] == 2

    def test_exact_page_count(self):
        params = PaginationParams(page=1, per_page=10)
        result = params.paginate([], total=30)
        assert result["pages"] == 3

    def test_single_page(self):
        params = PaginationParams(page=1, per_page=20)
        result = params.paginate(["a", "b", "c"], total=3)
        assert result["pages"] == 1

    def test_zero_total(self):
        params = PaginationParams(page=1, per_page=10)
        result = params.paginate([], total=0)
        assert result["pages"] == 0
        assert result["items"] == []

    def test_total_one(self):
        params = PaginationParams(page=1, per_page=10)
        result = params.paginate(["item"], total=1)
        assert result["pages"] == 1
