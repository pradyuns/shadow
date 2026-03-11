"""Text extraction from raw HTML.

Why BeautifulSoup over lxml:
- Zero C dependencies — simpler Docker builds, no compilation step
- Gracefully handles malformed HTML (competitor pages are often messy)
- For text extraction (not XPath queries or high-throughput XML parsing),
  BS4's html.parser is fast enough and more resilient

Design: Strategy pattern for future page-type-aware extraction.
The base extractor handles all page types now. When we add pricing/jobs
extractors, they register here and get dispatched by page_type.
"""

import hashlib
import re

import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger()

# Tags that never contain user-visible content
REMOVE_TAGS = {"script", "style", "noscript", "iframe", "svg", "head", "meta", "link"}


def extract_text(raw_html: str, css_selector: str | None = None, page_type: str = "other") -> dict:
    """Extract clean text from raw HTML.

    Returns:
        dict with:
            - extracted_text: Clean text content
            - text_hash: SHA-256 hash of the text (for dedup/change detection)
            - text_length: Character count
            - auto_upgrade_js: True if content looks JS-rendered (needs Playwright)
    """
    soup = BeautifulSoup(raw_html, "html.parser")

    # Remove non-content tags
    for tag in soup.find_all(REMOVE_TAGS):
        tag.decompose()

    # Apply CSS selector if specified
    if css_selector:
        selected = soup.select_one(css_selector)
        if selected:
            soup = selected

    # Extract text with newline separators
    text = soup.get_text(separator="\n", strip=True)

    # Normalize whitespace: collapse multiple blank lines, strip trailing spaces
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" +", " ", text)
    text = text.strip()

    # Compute hash for change detection.
    # SHA-256 chosen over MD5: no collision risk, and we store it so speed
    # difference is negligible. Comparing hashes is O(1) vs O(n) for full text.
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

    # Auto-upgrade detection: if httpx returned very little text, the page
    # probably needs JS rendering. <100 chars of text from a real webpage is
    # a strong signal of a JS-only SPA.
    auto_upgrade_js = len(text) < 100 and "<noscript" in raw_html.lower()

    return {
        "extracted_text": text,
        "text_hash": text_hash,
        "text_length": len(text),
        "auto_upgrade_js": auto_upgrade_js,
    }
