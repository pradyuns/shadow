"""Claude prompt templates for change classification.

Separated from the client so prompts can be:
- Version-controlled and reviewed independently
- A/B tested (swap prompts without changing client logic)
- Unit tested (verify prompt construction with known inputs)
"""

# The significance levels with concrete examples help Claude make consistent
# classifications. Without examples, "medium" vs "low" becomes subjective.
SYSTEM_PROMPT = """You are a competitive intelligence analyst. Your job is to analyze changes detected on competitor websites and classify their significance.

You will receive a unified diff showing what changed on a competitor's web page. Analyze the changes and provide a structured classification.

## Significance Levels

- **critical**: Major strategic moves. Examples: pricing changes of >20%, product discontinuation, acquisition announcement, major leadership change, complete rebrand.
- **high**: Important competitive signals. Examples: new product/feature launch, pricing changes <20%, new partnership announcement, significant messaging overhaul, expansion to new market.
- **medium**: Noteworthy updates. Examples: feature updates, new blog post about strategy, job postings in new departments, updated case studies, new integrations.
- **low**: Minor updates. Examples: small copy changes, bug fixes mentioned in changelog, minor UI updates, routine blog posts, updated team photos.
- **noise**: Not competitively relevant. Examples: typo fixes, footer updates, legal boilerplate changes, formatting changes, dependency version bumps.

## Categories (select all that apply)

- pricing_change: Changes to pricing, plans, billing, or monetization
- feature_launch: New feature, product, or capability announced
- feature_removal: Feature deprecated, removed, or sunset
- hiring_signal: New job postings, team growth, new departments
- messaging_change: Changes to positioning, value props, taglines, hero copy
- partnership: New integration, partnership, or ecosystem announcement
- technical_change: API changes, technical documentation updates, infrastructure
- other: Doesn't fit above categories

## Instructions

1. Focus on the SUBSTANCE of the changes, not formatting or styling
2. Consider the page_type context (a pricing page change is more significant than a blog page change)
3. Be concise in your summary — max 200 words
4. If the diff is mostly noise with a few real changes, focus on the real changes
5. When uncertain between two significance levels, choose the HIGHER one (false negatives cost more than false positives in competitive intelligence)
"""


def build_user_prompt(
    competitor_name: str | None,
    page_type: str,
    url: str,
    filtered_diff: str,
    truncated: bool = False,
) -> str:
    """Construct the user message containing the diff and context.

    Args:
        competitor_name: The competitor's name for context.
        page_type: Type of page (pricing, changelog, jobs, etc.).
        url: The monitored URL.
        filtered_diff: The noise-filtered diff to classify.
        truncated: Whether the diff was truncated to fit token budget.

    Returns:
        Formatted user prompt string.
    """
    parts = []

    parts.append(f"**Competitor**: {competitor_name or 'Unknown'}")
    parts.append(f"**Page Type**: {page_type}")
    parts.append(f"**URL**: {url}")

    if truncated:
        parts.append("\n⚠️ Note: This diff was truncated to fit the analysis budget. The full diff may contain additional changes.")

    parts.append(f"\n**Changes Detected**:\n```diff\n{filtered_diff}\n```")

    return "\n".join(parts)


# Token budget: ~4 chars per token for English text.
# 4000 tokens ≈ 16,000 chars. We leave room for the system prompt.
MAX_DIFF_CHARS = 14000


def truncate_diff(diff_text: str, max_chars: int = MAX_DIFF_CHARS) -> tuple[str, bool]:
    """Truncate a diff to fit within the token budget.

    We truncate at hunk boundaries where possible (cleaner than mid-line cuts).

    Returns:
        (truncated_diff, was_truncated)
    """
    if len(diff_text) <= max_chars:
        return diff_text, False

    # Try to cut at a hunk boundary
    lines = diff_text.split("\n")
    result_lines = []
    current_size = 0

    for line in lines:
        line_size = len(line) + 1  # +1 for newline
        if current_size + line_size > max_chars:
            break
        result_lines.append(line)
        current_size += line_size

    truncated = "\n".join(result_lines)
    truncated += "\n\n[... diff truncated ...]"
    return truncated, True
