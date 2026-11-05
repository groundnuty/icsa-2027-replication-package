"""The pull ledger: an append-only `ledger.jsonl` plus `chunks/<seq:06d>.log.gz`, one chunk per pull, the lines of the users asked for in [from_off, to_off) of site_g's log.

Rows (`seq` counts pulls and gaps together):
  pull: {seq, kind "pull", inode, from_off, to_off, size_at, pulled_utc, sha256 (of the uncompressed chunk), n_lines, chunk, complete, users_sha}
  gap:  {seq, kind "gap", inode (the one seen), from_off (the ledger's offset), to_off None, size_at None, pulled_utc, sha256 None, n_lines 0, chunk None, reason}
`complete` is True when the pull reached the file's end as stat saw it, False when `max_bytes` cut it short: only a complete pull says the ledger holds
everything written up to its `pulled_utc`. A gap row marks a refused pull and never moves the offset or the inode, so the next pull is judged against the last PULL.
The ledger is not the calibration ledger of `icsa/faults/ledger.py`.
"""
from __future__ import annotations

import contextlib
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path
from typing import Iterator


class LedgerError(RuntimeError):
    pass


def _fsync_dir(d: Path) -> None:
    fd = os.open(d, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Ledger:
    def __init__(self, root):
        self.root = Path(root)
        self.path = self.root / "ledger.jsonl"
        (self.root / "chunks").mkdir(parents=True, exist_ok=True)

    # ---- reading
    def rows(self) -> list[dict]:
        if not self.path.exists():
            return []
        text = self.path.read_bytes().decode("utf-8")
        if text and not text.endswith("\n"):
            raise LedgerError(f"{self.path}: the last row is torn (no newline): a person must look before anything is appended")
        out = []
        for n, ln in enumerate(text.split("\n")[:-1], 1):
            try:
                row = json.loads(ln)
            except ValueError as e:
                raise LedgerError(f"{self.path}:{n}: not JSON: {e}") from e
            if row.get("seq") != n:
                raise LedgerError(f"{self.path}:{n}: seq is {row.get('seq')}, expected {n}")
            out.append(row)
        return out

    def pulls(self) -> list[dict]:
        return [r for r in self.rows() if r["kind"] == "pull"]

    def last_pull(self) -> dict | None:
        p = self.pulls()
        return p[-1] if p else None

    def offset(self) -> int | None:
        """to_off of the last pull; None before the first. A gap row never moves it."""
        p = self.last_pull()
        return None if p is None else p["to_off"]

    def inode(self) -> int | None:
        p = self.last_pull()
        return None if p is None else p["inode"]

    def covered_until(self) -> float | None:
        """pulled_utc of the last COMPLETE pull (it reached the end of the file as stat saw it), else None. A pull cut short by max_bytes says nothing
        about the time up to now: during a backfill every pull is cut short, and the ledger is far behind."""
        done = [r["pulled_utc"] for r in self.pulls() if r.get("complete")]
        return done[-1] if done else None

    def gaps(self) -> list[tuple[float, float | None]]:
        """One (t0, t1) epoch span per run of consecutive refusals: t0 = pulled_utc of the last complete pull before it (else of the ledger's first row), t1 =
        pulled_utc of the first pull after it, None if there is none yet. Wide on purpose: a run that touches a span is not observed."""
        rows, out, i = self.rows(), [], 0
        while i < len(rows):
            if rows[i]["kind"] != "gap":
                i += 1
                continue
            j = i
            while j < len(rows) and rows[j]["kind"] == "gap":
                j += 1
            before = [r["pulled_utc"] for r in rows[:i] if r["kind"] == "pull" and r.get("complete")]
            t0 = before[-1] if before else rows[0]["pulled_utc"]
            out.append((t0, rows[j]["pulled_utc"] if j < len(rows) else None))
            i = j
        return out

    def _chunk_bytes(self, row: dict) -> bytes:
        raw = gzip.decompress((self.root / row["chunk"]).read_bytes())
        if hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise LedgerError(f"{row['chunk']}: sha256 does not match the ledger row {row['seq']}")
        return raw

    def iter_lines(self) -> Iterator[str]:
        """Every chunk's lines, in seq order, without the newline. A chunk whose bytes no longer match its row raises."""
        for row in self.pulls():
            yield from self._chunk_bytes(row).decode("utf-8", "replace").split("\n")[:-1]

    # ---- writing
    def _append_row(self, row: dict) -> dict:
        n = len(self.rows())                      # also refuses a torn or out-of-sequence ledger
        row = {"seq": n + 1, **row}
        with open(self.path, "ab") as f:
            f.write((json.dumps(row) + "\n").encode())
            f.flush()
            os.fsync(f.fileno())
        if n == 0:
            _fsync_dir(self.root)
        return row

    def append_pull(self, *, inode: int, from_off: int, to_off: int, size_at: int, pulled_utc: float, data: bytes, complete: bool, users_sha: str | None = None) -> dict:
        """Stores `data` (the filtered lines of [from_off, to_off)) and appends the row. Raises LedgerError unless from_off is the previous pull's to_off on the
        same inode: a pull is contiguous with the last one or it is not written."""
        if not 0 <= from_off <= to_off:
            raise LedgerError(f"bad span [{from_off}, {to_off})")
        if data and not data.endswith(b"\n"):
            raise LedgerError("a chunk is whole lines")
        prev = self.last_pull()
        if prev is not None and (inode != prev["inode"] or from_off != prev["to_off"]):
            raise LedgerError(f"not contiguous: the last pull ended at {prev['to_off']} of inode {prev['inode']}, this one starts at {from_off} of inode {inode}")
        seq = len(self.rows()) + 1
        chunk = f"chunks/{seq:06d}.log.gz"
        tmp = self.root / "chunks" / f".{seq:06d}.tmp"
        with open(tmp, "wb") as f:
            f.write(gzip.compress(data, mtime=0))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.root / chunk)
        _fsync_dir(self.root / "chunks")
        return self._append_row({"kind": "pull", "inode": inode, "from_off": from_off, "to_off": to_off, "size_at": size_at, "pulled_utc": pulled_utc,
                                 "sha256": hashlib.sha256(data).hexdigest(), "n_lines": data.count(b"\n"), "chunk": chunk, "complete": bool(complete),
                                 "users_sha": users_sha})

    def append_gap(self, inode: int, from_off: int, reason: str, pulled_utc: float) -> dict:
        """A refused pull. Nothing was read, so nothing moves: offset() and inode() still come from the last pull."""
        return self._append_row({"kind": "gap", "inode": inode, "from_off": from_off, "to_off": None, "size_at": None, "pulled_utc": pulled_utc,
                                 "sha256": None, "n_lines": 0, "chunk": None, "reason": reason})

    @contextlib.contextmanager
    def locked(self) -> Iterator[None]:
        """One puller at a time: a second one raises instead of reading the same bytes."""
        fd = os.open(self.root / "ledger.lock", os.O_CREAT | os.O_RDWR, 0o644)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as e:
                raise LedgerError(f"{self.root}: another pull holds the ledger") from e
            yield
        finally:
            os.close(fd)
