"""Which bytes of a file a REST response served: from status, Range header and body size."""
from __future__ import annotations

import re

_SPEC = re.compile(r"^\s*(\d*)\s*-\s*(\d*)\s*$")


def parse_range_header(header: str | None, size: int) -> list[tuple[int, int]] | None:
    """Half-open spans a `Range: bytes=...` header asks for, clipped to the file.

    Handles a-b, a- (to the end), -n (the last n bytes) and comma-separated multi-range.
    Returns None when the header is absent or malformed (a server then ignores it and serves 200).
    Unsatisfiable parts are dropped; if none are satisfiable the list is empty (a 416).
    """
    if not header:
        return None
    h = header.strip()
    if not h.lower().startswith("bytes="):
        return None
    out = []
    for part in h[6:].split(","):
        m = _SPEC.match(part)
        if not m or (m.group(1) == "" and m.group(2) == ""):
            return None
        a, b = m.group(1), m.group(2)
        if a == "":                      # suffix: last n bytes
            n = int(b)
            if n == 0:
                continue
            start, end = max(0, size - n), size
        else:
            start = int(a)
            end = size if b == "" else int(b) + 1
            if b != "" and int(b) < start:
                return None              # malformed (last < first): ignored by servers
        end = min(end, size)
        if start >= size or start >= end:
            continue
        out.append((start, end))
    return out


def served_spans(status: int | None, range_header: str | None, content_size: int | None,
                 size: int) -> list[tuple[int, int]] | None:
    """Spans actually sent; only bytes known to have been served are credited. None = cannot be resolved, never credited.

    - No body size logged: None, whatever the status (the record cannot say what was sent).
    - 200: the whole file whatever the header said, cut to the body size if the body was short.
    - 206, single range: the range, cut to the body size if the transfer was short.
    - 206, multi-range: None. The body size includes multipart framing and an access log has no per-part sizes, so the
      body cannot be mapped to its ranges (a 1-byte body would otherwise credit every part).
    - 206 with no usable Range header: None.
    """
    if status not in (200, 206):
        return []
    if content_size is None:
        return None
    if status == 200:
        end = min(size, max(0, content_size))
        return [(0, end)] if end > 0 else []
    spans = parse_range_header(range_header, size)
    if not spans or "," in range_header:         # several ranges asked: even with one left in the file, the body may be multipart
        return None
    a, b = spans[0]
    b = min(b, a + max(0, content_size))
    return [(a, b)] if b > a else []


def merge_spans(spans) -> list[tuple[int, int]]:
    """Union of half-open byte spans, sorted and disjoint (touching spans are joined)."""
    out: list[tuple[int, int]] = []
    for a, b in sorted((int(x), int(y)) for x, y in spans if y > x):
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def covers(merged: list[tuple[int, int]], a: int, b: int) -> bool:
    """Detector v2's byte rule: one span of the UNION covers every stored byte [a, b) of a chunk.
    `merged` must come from `merge_spans` (disjoint, so only the last span starting at or before `a` can)."""
    import bisect
    i = bisect.bisect_right([x for x, _ in merged], a) - 1
    return i >= 0 and merged[i][1] >= b
