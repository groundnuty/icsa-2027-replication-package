"""Shared types: a check result is PASS, FAIL or MISSING. MISSING is never PASS.

An artifact marked ``"stub": true`` is a placeholder for an input that does not exist yet
(#12 before it lands). A check on a stub reports MISSING, never PASS.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import pathlib
from typing import Any

PASS, FAIL, MISSING = "PASS", "FAIL", "MISSING"


@dataclasses.dataclass
class Evidence:
    path: str
    sha256: str | None
    note: str = ""


@dataclasses.dataclass
class CheckResult:
    number: int
    title: str
    status: str
    reasons: list[str]
    source: str                      # where the pass condition and its threshold come from
    evidence: list[Evidence] = dataclasses.field(default_factory=list)
    details: list[str] = dataclasses.field(default_factory=list)   # extra lines for the section


class Artifact:
    """A JSON/JSONL input: loaded bytes, hash, and a stub flag. `data` is None when absent."""

    def __init__(self, path: str | pathlib.Path | None, jsonl: bool = False):
        self.path = None if path is None else str(path)
        self.data: Any = None
        self.sha256: str | None = None
        self.error: str | None = None
        self.stub = False
        if path is None:
            self.error = "no path configured"
            return
        p = pathlib.Path(path)
        if not p.is_file():
            self.error = f"file not found: {p}"
            return
        raw = p.read_bytes()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        try:
            if jsonl:
                self.data = [json.loads(x) for x in raw.decode().splitlines() if x.strip()]
                self.stub = any(isinstance(r, dict) and r.get("stub") for r in self.data[:1])
            else:
                self.data = json.loads(raw)
                self.stub = isinstance(self.data, dict) and bool(self.data.get("stub"))
        except (ValueError, UnicodeDecodeError) as e:
            self.error = f"unreadable: {e}"
            self.data = None

    @property
    def usable(self) -> bool:
        return self.data is not None and not self.stub

    def why_unusable(self) -> str:
        if self.stub:
            return f"{self.path} is a stub (placeholder), not a real result"
        return self.error or "missing"

    def evidence(self, note: str = "") -> Evidence:
        return Evidence(self.path or "(none)", self.sha256, note)


def missing(number: int, title: str, source: str, *arts: Artifact) -> CheckResult:
    return CheckResult(number, title, MISSING, [a.why_unusable() for a in arts if not a.usable], source,
                       [a.evidence() for a in arts if a.path])


def overall(results: list[CheckResult]) -> str:
    fails = [r.number for r in results if r.status == FAIL]
    if fails:
        return "NO-GO: criterion " + ", ".join(map(str, fails)) + " fails"
    if all(r.status == PASS for r in results) and len(results) == 6:
        return "all six criteria pass"
    miss = [r.number for r in results if r.status == MISSING]
    return "INCOMPLETE: no criterion fails, but criterion " + ", ".join(map(str, miss)) + " has missing input"
