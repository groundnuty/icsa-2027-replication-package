"""One incremental pull of site_g's audit log into the ledger, and the time bisection that finds where to start.

`pull_once` reads only the bytes after the ledger's offset, cut at the last newline, filtered to the users at the source. It refuses (a gap row, then
`PullRefused`, and not one byte read) when the file is not the one the ledger followed: a sibling file, another inode, or a size below the offset. It never starts
over at 0, which would be a 9 GB read during main (silent-fallback rule B). A transport error is not a refusal: it propagates and writes nothing.

Known blind spot: a file truncated and then regrown past the offset on the same inode looks like a longer file, and the pull resumes there silently.
"""
from __future__ import annotations

import calendar
import hashlib
import re
import time
from typing import Callable, Sequence

from .ledger import Ledger
from .remote import MAX_RANGE, Remote, check_off, check_users

_TS = re.compile(rb"\[(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d)\.(\d{3})\]")
TS_LEN = 25                    # len("[2026-11-01 21:20:42.800]")
SLACK_S = 1.0                  # the source is time-ordered to about 20 ms; a second keeps the bisection safe


class PullRefused(RuntimeError):
    """The pull stopped on purpose; the ledger and the log are as they were (a gap row says so when the file itself was the reason)."""


def parse_ts(buf: bytes, at: int = 0) -> float | None:
    """Epoch seconds of the `[YYYY-MM-DD HH:MM:SS.mmm]` (UTC) that starts at buf[at], or None."""
    m = _TS.match(buf, at)
    if m is None:
        return None
    y, mo, d, h, mi, s, ms = map(int, m.groups())
    try:
        return calendar.timegm((y, mo, d, h, mi, s, 0, 0, 0)) + ms / 1000
    except (ValueError, OverflowError):
        return None


def users_sha(users: Sequence[str]) -> str:
    return hashlib.sha256("|".join(check_users(users)).encode()).hexdigest()[:16]


def _refuse(ledger: Ledger, inode: int, off: int, why: list[str] | str, pulled: float):
    why = why if isinstance(why, str) else "; ".join(why)
    ledger.append_gap(inode, off, why, pulled)
    raise PullRefused(why)


def _cut(remote: Remote, off: int, end: int) -> int | None:
    """The offset just after the last newline in [off, end), looking at the last 64 KiB only. `off` when no complete line is there yet (a half line:
    wait); None when the read came back short (the file shrank under us). A full 64 KiB window with no newline while there is more before it would
    stall every later pull while looking idle, so that raises."""
    lo = max(off, end - MAX_RANGE)
    if lo == end:
        return off
    buf = remote.read_range(lo, end - lo)
    if len(buf) != end - lo:
        return None
    i = buf.rfind(b"\n")
    if i >= 0:
        return lo + i + 1
    if lo == off:
        return off
    raise PullRefused(f"no line end in the {MAX_RANGE} bytes before {end}: a line longer than 64 KiB, so this is not an audit log; nothing was read or stored")


def pull_once(remote: Remote, ledger: Ledger, users: Sequence[str], *, max_bytes: int = 256 * 2 ** 20, start_offset: int | None = None,
              start_inode: int | None = None, min_size: int | None = None, end_limit: int | None = None, now: Callable[[], float] = time.time) -> dict:
    """One pull. `start_offset` (a line start, e.g. from offset_at_time) starts an EMPTY ledger and is ignored once the ledger has a pull; an empty ledger
    without one raises ValueError, never defaulting to 0. `start_inode` (the inode the bisection ran on) is checked the same way: a different file now means
    the offset is meaningless, so a gap and PullRefused. Returns {seq (None when only a partial line follows the offset), from_off, to_off, n_lines, size_at,
    behind, complete, pulled_utc}. `complete` (the ledger holds every line written before pulled_utc) needs the cut to reach the end of the file exactly:
    a capped pull, or a partial line at the end, leaves it False. A pull with nothing at all after the offset is a zero-line row with complete True, so that
    coverage moves on a quiet log."""
    users = check_users(users)
    if type(max_bytes) is not int or max_bytes < MAX_RANGE:
        raise ValueError(f"max_bytes must be an int of at least {MAX_RANGE}")
    usha = users_sha(users)
    prev = ledger.last_pull()
    if prev is None:
        if start_offset is None:
            raise ValueError("the first pull needs start_offset (offset_at_time): it never starts at 0")
        off = check_off(start_offset, "start_offset")
    else:
        if prev.get("users_sha") != usha:
            raise ValueError("this ledger was pulled for another set of users: a changed filter would leave holes in the earlier span; start a new store")
        off = prev["to_off"]
    pulled = now()                                     # before the stat, which fixes the extent: a line written after it is not claimed
    st = remote.stat()
    sib = remote.siblings()
    why = []
    if sib:
        why.append(f"rotated sibling(s) of the log: {sib}")
    if prev is not None and st.inode != prev["inode"]:
        why.append(f"the inode changed: the ledger follows {prev['inode']}, the file is {st.inode}")
    if prev is None and start_inode is not None and st.inode != start_inode:
        why.append(f"the inode changed since the bisection: it ran on {start_inode}, the file is {st.inode}, so the start offset means nothing")
    if st.size < off:
        why.append(f"the size {st.size} is below the offset {off}")
    elif min_size is not None and st.size < min_size:          # smaller than the caller saw (the backfill's starting EOF): refused before anything is committed
        why.append(f"the file shrank: {min_size} bytes were seen before this pull, now {st.size}")
    elif prev is not None and prev.get("size_at") is not None and st.size < prev["size_at"]:      # append-only: smaller than last seen is a truncation, even above the offset (Astra, delta P2)
        why.append(f"the file shrank on the same inode: the last pull saw {prev['size_at']} bytes, now {st.size}")
    if why:
        _refuse(ledger, st.inode, off, why, pulled)
    if prev is None and off > 0 and remote.read_range(off - 1, 1) != b"\n":
        raise ValueError(f"start_offset {off} is not a line start")
    if end_limit is not None and off >= end_limit:           # a backfill up to another segment's first byte: never past it (science, #34 08:52Z)
        return {"seq": None, "from_off": off, "to_off": off, "n_lines": 0, "size_at": st.size, "behind": 0, "complete": True, "pulled_utc": pulled}
    end_target = min(st.size, off + max_bytes, end_limit if end_limit is not None else st.size)
    e = _cut(remote, off, end_target)
    if e is None:
        _refuse(ledger, st.inode, off, "a read at the cut came back short: the file shrank during the pull", pulled)
    if st.size == off:                                  # nothing at all after the offset: an idle pull, and coverage moves on
        row = ledger.append_pull(inode=st.inode, from_off=off, to_off=off, size_at=st.size, pulled_utc=pulled, data=b"", complete=True, users_sha=usha)
        return {"seq": row["seq"], "from_off": off, "to_off": off, "n_lines": 0, "size_at": st.size, "behind": 0, "complete": True, "pulled_utc": pulled,
                "chunk": row["chunk"]}
    complete = e == st.size
    if e == off:
        return {"seq": None, "from_off": off, "to_off": off, "n_lines": 0, "size_at": st.size, "behind": st.size - off, "complete": complete, "pulled_utc": pulled}
    data = remote.read_filtered(off, e, users)
    after = remote.stat()
    if after.inode != st.inode or after.size < e:
        _refuse(ledger, after.inode, off, f"the file changed during the read (inode {st.inode} -> {after.inode}, size {st.size} -> {after.size}); the bytes read are dropped", pulled)
    row = ledger.append_pull(inode=st.inode, from_off=off, to_off=e, size_at=st.size, pulled_utc=pulled, data=data, complete=complete, users_sha=usha)
    return {"seq": row["seq"], "from_off": off, "to_off": e, "n_lines": row["n_lines"], "size_at": st.size, "behind": st.size - e, "complete": complete,
            "pulled_utc": pulled, "chunk": row["chunk"]}


def offset_at_time(remote: Remote, t_epoch: float, *, probe: int = 4096, max_probes: int = 200) -> int:
    """The byte offset of the first whole line whose timestamp is at or after t_epoch - 1 s, by bisection on the file's time order: about log2(size / probe)
    reads of at most `probe` bytes (22 for 9 GB), and never more than `max_probes` (RuntimeError: a log with no timestamps would otherwise be read to its end).
    The returned offset is a line start; no line stamped t_epoch or later lies before it. size when every line is older."""
    if type(probe) is not int or not 64 <= probe <= MAX_RANGE:
        raise ValueError(f"probe must be an int of 64..{MAX_RANGE}")
    size = remote.stat().size
    target = t_epoch - SLACK_S

    probes = 0

    def read(pos: int, n: int) -> bytes:
        nonlocal probes
        if probes >= max_probes:
            raise RuntimeError(f"offset_at_time: no timestamp found within {max_probes} probes")
        probes += 1
        buf = remote.read_range(pos, n)
        if len(buf) != n:
            raise RuntimeError(f"offset_at_time: asked {n} bytes at {pos} of {size}, got {len(buf)}: the file changed")
        return buf

    def locate(x: int) -> tuple[int, float]:
        """The first line that starts at or after x, and its time; (size, inf) if none. Reads from x - 1, since x alone cannot say whether it starts a line."""
        pos, at_start = max(x - 1, 0), x == 0
        while pos < size:
            buf = read(pos, min(probe, size - pos))
            b = 0
            if not at_start:
                j = buf.find(b"\n")
                if j < 0:
                    raise RuntimeError(f"offset_at_time: no line end within {probe} bytes at {pos}: a longer line than the probe")
                b = j + 1
            while b < len(buf):
                if len(buf) - b < TS_LEN and pos + len(buf) < size:      # the stamp is cut by the end of the probe: read again from this line
                    break
                ts = parse_ts(buf, b)
                if ts is not None:
                    return pos + b, ts
                j = buf.find(b"\n", b)
                if j < 0:                                                # this line runs past the probe: read again from it
                    break
                b = j + 1
            if pos + b >= size:
                break
            if b == 0:
                raise RuntimeError(f"offset_at_time: a line longer than the probe at {pos}")
            pos, at_start = pos + b, True
        return size, float("inf")

    s_lo, ts0 = locate(0)
    if ts0 >= target:
        return s_lo
    lo, hi = 0, size                    # P(lo): the first line from lo is older than target; P(hi): true (nothing at the end of the file)
    while hi - lo > probe:
        mid = (lo + hi) // 2
        s, ts = locate(mid)
        if ts >= target:
            hi = mid
        else:
            lo, s_lo = mid, s
    pos = s_lo                          # the first line at or after target starts in (s_lo, hi + one line]: walk the lines from s_lo
    while pos < size:
        buf = read(pos, min(probe, size - pos))
        b = 0
        while b < len(buf):
            if len(buf) - b < TS_LEN and pos + len(buf) < size:
                break
            ts = parse_ts(buf, b)
            if ts is not None and ts >= target:
                return pos + b
            j = buf.find(b"\n", b)
            if j < 0:
                break
            b = j + 1
        if b == 0:
            raise RuntimeError(f"offset_at_time: a line longer than the probe at {pos}")
        pos += b
    return size
