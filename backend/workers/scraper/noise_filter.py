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
from dataclasses import dataclass, field

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

@dataclass(frozen=True)
class CompiledNoisePattern:
    regex: re.Pattern
    source: str
    pattern: str


def _compile_patterns(patterns: list[str], source: str) -> list[CompiledNoisePattern]:
    compiled: list[CompiledNoisePattern] = []
    for pattern in patterns:
        try:
            compiled.append(
                CompiledNoisePattern(
                    regex=re.compile(pattern, re.IGNORECASE),
                    source=source,
                    pattern=pattern,
                )
            )
        except re.error:
            logger.warning("invalid_noise_pattern_skipped", pattern=pattern, source=source)
    return compiled


# Pre-compile for performance — these run on every diff line
_compiled_global = _compile_patterns(GLOBAL_NOISE_PATTERNS, source="global")


@dataclass
class FilterResult:
    """Result of filtering a unified diff."""

    filtered_diff: str
    original_lines: int
    noise_lines_removed: int
    is_empty_after_filter: bool
    learned_noise_lines_removed: int = 0
    learned_pattern_hits: dict[str, int] = field(default_factory=dict)


def _classify_noise_line(line: str, compiled_patterns: list[CompiledNoisePattern | re.Pattern]) -> tuple[bool, set[str]]:
    """Check if a diff line's content is entirely explained by noise patterns.

    A line is noise if removing all noise-pattern matches leaves only whitespace
    or very short content (<5 chars). This prevents false positives where a
    genuinely changed line happens to contain a timestamp alongside real content.
    """
    if line.startswith("+") or line.startswith("-"):
        cleaned = line[1:]
    else:
        cleaned = line
    matched_learned_patterns: set[str] = set()
    for pattern_entry in compiled_patterns:
        if isinstance(pattern_entry, CompiledNoisePattern):
            pattern = pattern_entry.regex
            source = pattern_entry.source
            raw_pattern = pattern_entry.pattern
        else:
            pattern = pattern_entry
            source = "legacy"
            raw_pattern = pattern.pattern

        updated = pattern.sub("", cleaned)
        if updated != cleaned and source == "learned":
            matched_learned_patterns.add(raw_pattern)
        cleaned = updated

    # Strip diff markers (+/-) and whitespace
    cleaned = cleaned.strip()

    # If almost nothing meaningful remains, it's noise
    return len(cleaned) < 5, matched_learned_patterns


def _is_noise_line(line: str, compiled_patterns: list[CompiledNoisePattern | re.Pattern]) -> bool:
    return _classify_noise_line(line, compiled_patterns)[0]


def filter_diff(
    unified_diff: str,
    monitor_noise_patterns: list[str] | None = None,
    learned_noise_patterns: list[str] | None = None,
) -> FilterResult:
    """Filter noise from a unified diff.

    Args:
        unified_diff: The raw unified diff string.
        monitor_noise_patterns: Additional regex patterns specific to this monitor.
        learned_noise_patterns: Auto-learned per-monitor patterns promoted by adaptive learning.

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

    compiled_custom = _compile_patterns(monitor_noise_patterns or [], source="monitor")
    compiled_learned = _compile_patterns(learned_noise_patterns or [], source="learned")
    all_patterns: list[CompiledNoisePattern] = _compiled_global + compiled_custom + compiled_learned

    lines = unified_diff.split("\n")
    filtered_lines = []
    noise_count = 0
    learned_noise_count = 0
    learned_hits: dict[str, int] = {}
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
            is_noise, matched_learned_patterns = _classify_noise_line(line, all_patterns)
            if is_noise:
                noise_count += 1
                if matched_learned_patterns:
                    learned_noise_count += 1
                    for matched in matched_learned_patterns:
                        learned_hits[matched] = learned_hits.get(matched, 0) + 1
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
        learned_noise_lines_removed=learned_noise_count,
        learned_pattern_hits=learned_hits,
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
