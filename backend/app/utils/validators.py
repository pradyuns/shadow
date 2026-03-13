import ipaddress
import re
import socket
from urllib.parse import urlparse


def _is_ip_safe(ip_str: str) -> bool:
    """Check if an IP address is safe (not private/loopback/reserved)."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)
    except ValueError:
        return True


def validate_url_safe(url: str) -> tuple[bool, str | None]:
    """Validate a URL is safe to scrape (no SSRF).

    Checks both the hostname directly and resolves DNS to catch
    domains that point to private/internal IP addresses.

    DNS lookup is best-effort here: monitor creation should not fail
    just because the current environment cannot resolve a public host.
    """
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

    # Block private IPs (direct IP in URL)
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False, "URLs pointing to private/reserved IP addresses are not allowed"
    except ValueError:
        # hostname is a domain name — resolve it to check the IP
        try:
            resolved_ips = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            for family, _, _, _, sockaddr in resolved_ips:
                ip_str = sockaddr[0]
                if not _is_ip_safe(ip_str):
                    return False, "URL resolves to a private/reserved IP address"
        except socket.gaierror:
            return True, None

    return True, None


def validate_regex_pattern(pattern: str) -> tuple[bool, str | None]:
    """Validate a regex pattern is safe to use."""
    # Length check first — before compilation
    if len(pattern) > 500:
        return False, "Regex pattern is too long (max 500 characters)"

    # Check for known ReDoS patterns (nested quantifiers)
    if re.search(r"\(.+[*+]\).+[*+]", pattern):
        return False, "Regex pattern contains potentially dangerous nested quantifiers"

    try:
        re.compile(pattern)
        return True, None
    except re.error as e:
        return False, f"Invalid regex pattern: {e}"
