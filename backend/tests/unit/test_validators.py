"""Tests for URL and regex validators."""

import pytest

from app.utils.validators import validate_regex_pattern, validate_url_safe


class TestValidateUrlSafe:
    """Test SSRF protection in URL validation."""

    def test_valid_https_url(self):
        ok, err = validate_url_safe("https://example.com/pricing")
        assert ok is True
        assert err is None

    def test_valid_http_url(self):
        ok, err = validate_url_safe("http://competitor.io/changelog")
        assert ok is True
        assert err is None

    def test_rejects_localhost(self):
        ok, err = validate_url_safe("http://localhost:8000/admin")
        assert ok is False
        assert "localhost" in err.lower()

    def test_rejects_127_0_0_1(self):
        ok, err = validate_url_safe("http://127.0.0.1/secret")
        assert ok is False

    def test_rejects_ipv6_loopback(self):
        ok, err = validate_url_safe("http://[::1]/admin")
        assert ok is False

    def test_rejects_zero_ip(self):
        ok, err = validate_url_safe("http://0.0.0.0/")
        assert ok is False

    def test_rejects_private_10_range(self):
        ok, err = validate_url_safe("http://10.0.0.1/internal")
        assert ok is False
        assert "private" in err.lower()

    def test_rejects_private_172_range(self):
        ok, err = validate_url_safe("http://172.16.0.1/")
        assert ok is False

    def test_rejects_private_192_168(self):
        ok, err = validate_url_safe("http://192.168.1.1/")
        assert ok is False

    def test_rejects_ftp_scheme(self):
        ok, err = validate_url_safe("ftp://example.com/file.txt")
        assert ok is False
        assert "HTTP" in err

    def test_rejects_file_scheme(self):
        ok, err = validate_url_safe("file:///etc/passwd")
        assert ok is False

    def test_rejects_no_hostname(self):
        ok, err = validate_url_safe("http://")
        assert ok is False

    def test_rejects_empty_string(self):
        ok, err = validate_url_safe("")
        assert ok is False

    def test_accepts_public_ip(self):
        ok, err = validate_url_safe("http://8.8.8.8/")
        assert ok is True

    def test_accepts_domain_with_subdomain(self):
        ok, err = validate_url_safe("https://www.competitor.com/pricing")
        assert ok is True

    def test_accepts_url_with_port(self):
        ok, err = validate_url_safe("https://example.com:8443/api")
        assert ok is True

    def test_accepts_url_with_path_and_query(self):
        ok, err = validate_url_safe("https://example.com/page?foo=bar&baz=1")
        assert ok is True


class TestValidateRegexPattern:
    """Test regex pattern validation."""

    def test_valid_simple_pattern(self):
        ok, err = validate_regex_pattern(r"\d{4}-\d{2}-\d{2}")
        assert ok is True
        assert err is None

    def test_valid_word_pattern(self):
        ok, err = validate_regex_pattern(r"price:\s*\$\d+")
        assert ok is True

    def test_rejects_invalid_regex(self):
        ok, err = validate_regex_pattern(r"[unclosed")
        assert ok is False
        assert "Invalid regex" in err

    def test_rejects_too_long_pattern(self):
        ok, err = validate_regex_pattern("a" * 501)
        assert ok is False
        assert "too long" in err.lower()

    def test_accepts_max_length_pattern(self):
        ok, err = validate_regex_pattern("a" * 500)
        assert ok is True

    def test_empty_pattern_is_valid(self):
        ok, err = validate_regex_pattern("")
        assert ok is True

    def test_complex_but_valid_pattern(self):
        ok, err = validate_regex_pattern(r"(?:https?://)?[\w.-]+\.\w{2,}")
        assert ok is True
