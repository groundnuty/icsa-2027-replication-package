"""The output cap, applied identically to every tool output in every option.

The cap is in characters ("8,000 characters per tool result entering the context",
protocol/parameters.md). The truncation notice counts inside the cap.
"""
from __future__ import annotations

TRUNCATION_NOTICE = "\n[output truncated: {dropped} of {total} characters dropped by the harness cap]"


def cap_text(text: str, cap_chars: int) -> tuple[str, bool]:
    """Cap `text` to at most `cap_chars` characters, notice included.

    Returns (delivered_text, was_truncated).
    """
    total = len(text)
    if total <= cap_chars:
        return text, False
    keep = cap_chars
    for _ in range(8):   # the notice's length depends on the digits of `dropped`; settle on a fixed point
        notice = TRUNCATION_NOTICE.format(dropped=total - keep, total=total)
        new_keep = cap_chars - len(notice)
        if new_keep < 0:
            return text[:cap_chars], True          # cap smaller than the notice: plain cut
        if new_keep == keep:
            break
        keep = new_keep
    notice = TRUNCATION_NOTICE.format(dropped=total - keep, total=total)
    out = text[:keep] + notice
    while len(out) > cap_chars and keep > 0:
        keep -= 1
        out = text[:keep] + TRUNCATION_NOTICE.format(dropped=total - keep, total=total)
    return out, True
