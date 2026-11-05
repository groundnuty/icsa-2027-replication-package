"""Find and redact secrets in text before it is archived.

Two detectors: exact values (read from the secret files the coder's container could see, matched literally and in their
JSON-escaped form) and token shapes (the common key formats). A finding is a kind and a span, never the matched value, and
`redact` writes `[REDACTED:<how>:<name>]` in its place, so the archived text and the report carry no secret.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

MIN_EXACT_LEN = 16   # a shorter file value is too likely to be ordinary text to redact everywhere it occurs

# Ordered: on a tie the earlier name labels the finding (an Anthropic key also fits the OpenAI shape).
TOKEN_SHAPES = (
    ("anthropic_key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("openai_key", re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}")),   # no lookbehind: it would miss a key after %22 or %3D; "task-force-..." over-redacts
    ("github_token", re.compile(r"gh[opsur]_[A-Za-z0-9]{20,}")),
    ("github_pat", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    # the header, and the whole block when its END line follows
    ("pem_private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----(?:[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----)?")),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("bearer", re.compile(r"\bbearer\s+[A-Za-z0-9._~+/-]{20,}", re.IGNORECASE)),
)


def _leaves(node, path: str):
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from _leaves(v, f"{path}.{k}" if path else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _leaves(v, f"{path}.{i}" if path else str(i))


def exact_values_from_files(paths) -> list[tuple[str, str]]:
    """(kind, value) pairs to match literally. A missing file is skipped; an unreadable one raises, so no secret is skipped silently.

    A JSON object or array gives every string leaf of at least 16 characters (kind `<file>:<dotted.key.path>`); any other
    file gives its stripped content if that is at least 16 characters (kind `<file>`). A bare number or quoted string is
    not JSON for this purpose: a key file of digits must not be read as a number and dropped.
    """
    pairs: list[tuple[str, str]] = []
    for p in paths:
        path = Path(p)
        if not path.exists():
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise ValueError(f"{path.name}: not UTF-8") from None     # the codec's own message quotes a byte
        try:
            doc = json.loads(raw)
        except ValueError:
            doc = None
        if isinstance(doc, (dict, list)):
            pairs += [(f"{path.name}:{k}", v) for k, v in _leaves(doc, "") if len(v) >= MIN_EXACT_LEN]
        elif len(raw.strip()) >= MIN_EXACT_LEN:
            pairs.append((path.name, raw.strip()))
    return pairs


def _forms(value: str) -> list[str]:
    """The value as written, and as it appears inside a JSON string (ASCII-escaped or not)."""
    return list(dict.fromkeys([value, json.dumps(value)[1:-1], json.dumps(value, ensure_ascii=False)[1:-1]]))


def scan(text: str, exact=()) -> list[dict]:
    """Findings `{"kind", "start", "end", "how": "exact"|"shape"}`, sorted, non-overlapping, never the value.

    `exact` is (kind, value) pairs. Overlapping matches merge into one finding spanning both; if any of them is an exact
    value the finding is `exact`, with that value's kind.
    """
    spans = []   # (start, end, how, kind); exact first, so on a tie it labels the merged finding
    for kind, value in exact:
        for form in (_forms(value) if value else ()):
            i = text.find(form)
            while i >= 0:
                spans.append((i, i + len(form), "exact", kind))
                i = text.find(form, i + len(form))
    for name, rx in TOKEN_SHAPES:
        spans += [(m.start(), m.end(), "shape", name) for m in rx.finditer(text)]
    out: list[dict] = []
    for s, e, how, kind in sorted(spans, key=lambda x: (x[0], -x[1])):
        if out and s < out[-1]["end"]:
            last = out[-1]
            last["end"] = max(last["end"], e)
            if how == "exact" and last["how"] != "exact":
                last["how"], last["kind"] = how, kind
        else:
            out.append({"kind": kind, "start": s, "end": e, "how": how})
    return out


def redact(text: str, exact=()) -> tuple[str, list[dict]]:
    """The text with each finding replaced by `[REDACTED:<how>:<shape name or 'exact'>]`, and the findings (spans of the original text)."""
    found, parts, pos = scan(text, exact), [], 0
    for f in found:
        parts += [text[pos:f["start"]], f"[REDACTED:{f['how']}:{f['kind'] if f['how'] == 'shape' else 'exact'}]"]
        pos = f["end"]
    parts.append(text[pos:])
    return "".join(parts), found
