"""Text diffing module using Python's difflib.

Why difflib.unified_diff:
- Stdlib, zero dependencies
- Line-level diffing matches our use case (content monitoring, not char-level edits)
- Unified format is compact, human-readable, and easy to render in frontend
- Context lines help reviewers understand what changed

Why NOT diff-match-patch (Google):
- Character-level granularity creates noisy diffs for text content
- Overkill for our use case — we care about "a paragraph was added/removed",
  not "character at position 47 changed"

Why NOT DOM/HTML diffing:
- We diff extracted TEXT, not raw HTML. DOM diffs show every attribute change,
  class reorder, and whitespace shift as a change — pure noise for content monitoring.
"""

import difflib
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class DiffResult:
    """Structured result from text diffing."""

    unified_diff: str
    lines_added: int
    lines_removed: int
    changed_hunks: int
    diff_size_bytes: int
    is_identical: bool


def compute_text_diff(
    text_before: str,
    text_after: str,
    context_lines: int = 3,
    monitor_name: str = "unknown",
) -> DiffResult:
    """Compute a unified diff between two text versions.

    Args:
        text_before: The previous version's extracted text.
        text_after: The current version's extracted text.
        context_lines: Number of surrounding context lines in the diff.
            3 is the standard (same as `diff -u`). More context helps
            Claude understand the change, but increases token count.
        monitor_name: For logging, helps identify which monitor produced this diff.

    Returns:
        DiffResult with the unified diff and metadata.
    """
    # Split into lines for difflib
    before_lines = text_before.splitlines(keepends=True)
    after_lines = text_after.splitlines(keepends=True)

    # Generate unified diff
    diff_lines = list(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile="previous",
            tofile="current",
            n=context_lines,
        )
    )

    if not diff_lines:
        return DiffResult(
            unified_diff="",
            lines_added=0,
            lines_removed=0,
            changed_hunks=0,
            diff_size_bytes=0,
            is_identical=True,
        )

    unified_diff = "".join(diff_lines)

    # Count added/removed lines
    lines_added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    lines_removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))

    # Count hunks (sections starting with @@)
    changed_hunks = sum(1 for line in diff_lines if line.startswith("@@"))

    logger.info(
        "diff_computed",
        monitor=monitor_name,
        lines_added=lines_added,
        lines_removed=lines_removed,
        hunks=changed_hunks,
    )

    return DiffResult(
        unified_diff=unified_diff,
        lines_added=lines_added,
        lines_removed=lines_removed,
        changed_hunks=changed_hunks,
        diff_size_bytes=len(unified_diff.encode("utf-8")),
        is_identical=False,
    )
