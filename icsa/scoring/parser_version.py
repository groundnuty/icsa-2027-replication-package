"""The parser's version, which the report spec asks every scored run to record. It sits beside the parser, so that the file it
names stays frozen."""
from __future__ import annotations

import functools
import hashlib
import subprocess
from pathlib import Path

PARSER = Path(__file__).with_name("report.py")


@functools.lru_cache(maxsize=1)
def parser_version() -> dict[str, str | None]:
    """The parser's commit, the last that changed its file, with `-dirty` if the file differs from it; and the hash of its
    content. A tree copied without its git history, as `bin/vmsync` copies one, has no commit (None), and the hash still
    names the version."""
    def git(*a: str) -> str:
        try:
            return subprocess.run(["git", "-C", str(PARSER.parent), *a], capture_output=True, text=True, timeout=30).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""
    commit = git("log", "-1", "--format=%H", "--", PARSER.name)
    if commit and git("status", "--porcelain", "--", PARSER.name):
        commit += "-dirty"
    return {"commit": commit or None, "sha256": hashlib.sha256(PARSER.read_bytes()).hexdigest()}
