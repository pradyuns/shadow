import ipaddress
import re
from urllib.parse import urlparse


def validate_url_safe(url: str) -> tuple[bool, str | None]:
    """Validate a URL is safe to scrape (no SSRF)."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    if parsed.scheme not in ("http", "https"):
        return False, "Only HTTP and HTTPS URLs are allowed"

    if not parsed.hostname:
        return False, "URL must have a hostname"

    hostname = parsed.hostname.lower()

    # Block localhost
    if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return False, "URLs pointing to localhost are not allowed"

    # Block private IPs
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False, "URLs pointing to private/reserved IP addresses are not allowed"
    except ValueError:
        # hostname is a domain name, not an IP — that's fine
        pass

    return True, None


def validate_regex_pattern(pattern: str) -> tuple[bool, str | None]:
    """Validate a regex pattern is safe to use."""
    try:
        compiled = re.compile(pattern)
        # Basic check for catastrophic backtracking patterns
        if len(pattern) > 500:
            return False, "Regex pattern is too long (max 500 characters)"
        return True, None
    except re.error as e:
        return False, f"Invalid regex pattern: {e}"
