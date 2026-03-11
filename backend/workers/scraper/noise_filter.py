"""Noise filtering for diffs — removes changes that are purely cosmetic/ephemeral.

Why filter before Claude (not after):
- Cost control: Claude API calls cost money per token. Filtering noisy diffs
  before sending to Claude saves 60-80% of API costs.
- Accuracy: Claude can be confused by noise — timestamps, session IDs, and
  build hashes make diffs look significant when they're not.
- Speed: Filtering is milliseconds; Claude classification is 1-5 seconds.

Design: Global patterns (applied to all monitors) + per-monitor custom patterns.
Patterns are applied to individual diff lines, not the entire diff. A hunk is
removed only if ALL its changed lines are noise.
"""

import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()

# Global noise patterns — match common ephemeral content across all sites.
# These are applied to every diff. Per-monitor patterns are additive.
GLOBAL_NOISE_PATTERNS = [
    # Timestamps in various formats
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?",
    r"\d{10,13}",  # Unix epoch timestamps
    # Cache-busting hashes in asset URLs
    r"[a-f0-9]{8,32}(?=\.(js|css|png|jpg|svg|woff2?))",
    r"bundle\.[a-f0-9]+\.js",
    r"chunk-[a-f0-9]+",
    # Session/auth tokens
    r"csrf[_-]?token[\"':\s=]+[\"']?[\w-]+",
    r"session[_-]?id[\"':\s=]+[\"']?[\w-]+",
    r"nonce[\"':\s=]+[\"']?[\w-]+",
    # Tracking parameters
    r"utm_\w+=[^&\s]+",
    r"fbclid=[^&\s]+",
    r"gclid=[^&\s]+",
    # Ad slots and trackers
    r"ad[-_]?slot",
    r"google[_-]?ad",
    r"doubleclick",
    r"googletag",
    # Copyright years
    r"©\s*\d{4}",
    r"[Cc]opyright\s+\d{4}",
    # Cookie consent / banner IDs
    r"cookie[-_]?consent",
    r"cookie[-_]?banner",
    r"__cf_bm=",  # Cloudflare bot management
]

# Pre-compile for performance — these run on every diff line
_compiled_global = [re.compile(p, re.IGNORECASE) for p in GLOBAL_NOISE_PATTERNS]


@dataclass
class FilterResult:
    """Result of filtering a unified diff."""

    filtered_diff: str
    original_lines: int
    noise_lines_removed: int
    is_empty_after_filter: bool


def _is_noise_line(line: str, compiled_patterns: list[re.Pattern]) -> bool:
    """Check if a diff line's content is entirely explained by noise patterns.

    A line is noise if removing all noise-pattern matches leaves only whitespace
    or very short content (<5 chars). This prevents false positives where a
    genuinely changed line happens to contain a timestamp alongside real content.
    """
    cleaned = line
    for pattern in compiled_patterns:
        cleaned = pattern.sub("", cleaned)

    # Strip diff markers (+/-) and whitespace
    cleaned = cleaned.lstrip("+-").strip()

    # If almost nothing meaningful remains, it's noise
    return len(cleaned) < 5


def filter_diff(unified_diff: str, monitor_noise_patterns: list[str] | None = None) -> FilterResult:
    """Filter noise from a unified diff.

    Args:
        unified_diff: The raw unified diff string.
        monitor_noise_patterns: Additional regex patterns specific to this monitor.

    Returns:
        FilterResult with the cleaned diff and stats.
    """
    if not unified_diff or not unified_diff.strip():
        return FilterResult(
            filtered_diff="",
            original_lines=0,
            noise_lines_removed=0,
            is_empty_after_filter=True,
        )

    # Compile per-monitor patterns (validated at monitor creation time, so safe here)
    compiled_custom = []
    for pattern_str in monitor_noise_patterns or []:
        try:
            compiled_custom.append(re.compile(pattern_str, re.IGNORECASE))
        except re.error:
            logger.warning("invalid_noise_pattern_skipped", pattern=pattern_str)

    all_patterns = _compiled_global + compiled_custom

    lines = unified_diff.split("\n")
    filtered_lines = []
    noise_count = 0
    total_changed = 0

    # Process the diff preserving hunk structure.
    # We keep context lines (no +/-) and hunk headers (@@) always.
    # Only changed lines (+/-) are candidates for noise filtering.
    i = 0
    while i < len(lines):
        line = lines[i]

        # Keep diff headers and hunk markers unconditionally
        if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
            filtered_lines.append(line)
            i += 1
            continue

        # Changed lines: check if noise
        if line.startswith("+") or line.startswith("-"):
            total_changed += 1
            if _is_noise_line(line, all_patterns):
                noise_count += 1
                i += 1
                continue

        # Context lines and non-noise changed lines: keep
        filtered_lines.append(line)
        i += 1

    # Clean up: remove empty hunks (hunk headers followed by only context or nothing)
    final_lines = _remove_empty_hunks(filtered_lines)
    filtered_diff = "\n".join(final_lines)

    # Check if anything meaningful remains
    has_changes = any(
        l.startswith("+") or l.startswith("-")
        for l in final_lines
        if not l.startswith("---") and not l.startswith("+++")
    )

    return FilterResult(
        filtered_diff=filtered_diff,
        original_lines=total_changed,
        noise_lines_removed=noise_count,
        is_empty_after_filter=not has_changes,
    )


def _remove_empty_hunks(lines: list[str]) -> list[str]:
    """Remove hunk headers that have no actual changes beneath them."""
    result = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("@@"):
            # Peek ahead to see if this hunk has any changes
            hunk_lines = [lines[i]]
            j = i + 1
            has_changes = False
            while j < len(lines) and not lines[j].startswith("@@"):
                hunk_lines.append(lines[j])
                if lines[j].startswith("+") or lines[j].startswith("-"):
                    if not lines[j].startswith("---") and not lines[j].startswith("+++"):
                        has_changes = True
                j += 1

            if has_changes:
                result.extend(hunk_lines)
            i = j
        else:
            result.append(lines[i])
            i += 1

    return result
