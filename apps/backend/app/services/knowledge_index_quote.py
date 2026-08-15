from __future__ import annotations


def estimate_normalized_markdown_tokens(markdown: str) -> int:
    """Return the deterministic mvp-v1 estimate for indexable Markdown.

    The input must already be parser output, never an original container's
    bytes. Keeping this helper format-agnostic prevents PDF/DOCX assets from
    being charged as though they were user text.
    """

    normalized = markdown.strip()
    if not normalized:
        return 0
    return (len(normalized.encode("utf-8")) + 3) // 4
