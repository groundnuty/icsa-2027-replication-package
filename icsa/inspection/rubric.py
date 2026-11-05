"""Where the rubric is read from, and its hash (recorded in every artifact).

The rubric is amendment 11, frozen on main as `protocol/inspection-rubric.md` (sha256 50e91fa2...,
timestamped on OSF at 20:20Z on 1 Nov 2026). Any change to it is a dated amendment made only through
the science agent. It is read at use time; ICSA_INSPECTION_RUBRIC overrides the path for tests only.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROTOCOL = REPO / "protocol" / "inspection-rubric.md"
FROZEN_SHA256 = "50e91fa231731a29a04842fb5ee933b456cc479d85b5a063936079a858efc8ac"   # amendment 11 as registered


def path(override=None) -> Path:
    p = override or os.environ.get("ICSA_INSPECTION_RUBRIC")
    return Path(p) if p else PROTOCOL


def info(override=None) -> dict:
    """{'path', 'sha256', 'first_line', 'matches_registered'}; sha256 None when the file cannot be read
    (stated, not hidden). `matches_registered` says whether it is amendment 11 as frozen."""
    p = path(override)
    try:
        data = p.read_bytes()
    except OSError as e:
        return {"path": str(p), "sha256": None, "first_line": None, "matches_registered": False,
                "error": f"{type(e).__name__}"}
    h = hashlib.sha256(data).hexdigest()
    return {"path": str(p), "sha256": h, "matches_registered": h == FROZEN_SHA256,
            "first_line": data.decode("utf-8", "replace").splitlines()[0] if data else ""}
