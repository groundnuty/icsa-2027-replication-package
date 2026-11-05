"""Is site_g solo? (science, #34 07:46Z: before the solo T probe, show that nothing from `.8` reads site_g.) site_g's node cannot tell sources apart (kube-proxy SNATs every
client to one address in the pod, and there is no conntrack), but the audit log names the Onedata user of every request, and the slot users are partitioned
by host. So: read the last N minutes of site_g's audit log (one bounded tail read at EOF, filtered to the slot users in the pod under nice and ionice), take the
slot users seen, subtract the users `.23` holds a lease on now and any key the caller excludes (the probe's own), and name every user left with its slot key
and the host (or process) that owns the key.

The answer is never "solo" by default (silent-fallback rule B):
  * the tail read must reach back past the window's start (its first line no later than now - N min), else it is INCONCLUSIVE and says how far it reached;
  * `.23`'s leases are read from its lease dir and /proc/locks, read-only (a lock file's inode against the kernel's table of held locks: no lock is taken,
    unlike `slot_lease._lock_held`); a read that fails is INCONCLUSIVE.
Exit 0 solo, 2 NOT solo (users listed), 3 inconclusive."""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Callable, Sequence

from .pull import parse_ts

LEASE_DIR_23 = "/mnt/volume2/icsa-2027/slot-leases"
SSH_23 = ("ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", "-o", "IdentitiesOnly=yes", "-i", "~/.secrets/icsa-2027/runvm_ed25519",
          "-o", "UserKnownHostsFile=~/.secrets/icsa-2027/runvm_known_hosts", "email-1@example")
# read-only: each lock file's inode and device, then the kernel's table of held locks; any failing step fails the command (no ICSA_RC=0)
LEASES_CMD = (f'cd {LEASE_DIR_23} || exit 9; for f in *.lock; do [ -e "$f" ] || continue; s=$(stat -c "%i %D" "$f") || exit 9; echo "L $s $f"; done; '
              "echo ICSA_LOCKS; cat /proc/locks || exit 9; echo ICSA_RC=0")
_HEAD = re.compile(rb"^\[[^\]]*\] request: [^;]*; user: ([A-Za-z0-9]*);")
# only what a lease is: an exclusive flock (slot_lease takes LOCK_EX), held, not a waiter ("->")
_LOCK = re.compile(r"^\d+:\s+FLOCK\s+\S+\s+WRITE\s+\d+\s+([0-9a-f]+):([0-9a-f]+):(\d+)\s")
COVER_SLACK_S = 1.0          # the source is time-ordered only to about 20 ms (pull.py): the first line must lie this far before the window
SETTLE_S = 1.0               # between the read and the second stat, for a line partial at the first


def held_keys(out: str) -> list[str]:
    """The slot keys whose lock file the kernel lists as exclusively flocked, from LEASES_CMD's output. Raises if the output is not whole."""
    if "ICSA_LOCKS" not in out or not out.rstrip().endswith("ICSA_RC=0"):
        raise RuntimeError(f".23 lease read: the output is not whole: {out[-300:]!r}")
    files, locks = out.split("ICSA_LOCKS", 1)
    inode_key = {}
    for ln in files.splitlines():
        p = ln.split()
        if len(p) == 4 and p[0] == "L" and p[3].endswith(".lock"):
            inode_key[(int(p[1]), int(p[2], 16))] = p[3][:-len(".lock")]
    held = set()
    for ln in locks.splitlines():
        if "->" in ln:
            continue
        m = _LOCK.match(ln.strip())
        if m:
            dev = os.makedev(int(m.group(1), 16), int(m.group(2), 16))      # st_dev's encoding (stat %D), minors above 255 included
            k = inode_key.get((int(m.group(3)), dev))
            if k:
                held.add(k)
    return sorted(held)


def owners(launch: dict) -> dict[str, str]:
    """slot key -> who owns it: a run host (launch `hosts`), the live check's probe, or a process reservation (lent from a host's keys)."""
    out = {}
    for host, spec in (launch.get("hosts") or {}).items():
        for k in spec.get("slot_keys", []):
            out[k] = host
    for shape, k in (launch.get("live_check_slot_keys") or {}).items():
        out[k] = f"live-check probe ({shape})" + (f", in {out[k]}'s keys" if k in out else "")
    for name, spec in (launch.get("process_reservations") or {}).items():
        for k in spec.get("slot_keys", []):
            out[k] = f"reservation {name}" + (f", lent from {out[k]}" if k in out else "")
    return out


def _cut(remote, lo: int, size: int) -> int:
    w = max(lo, size - 65536)
    tail = remote.read_range(w, size - w) if size > w else b""
    k = tail.rfind(b"\n")
    return w + k + 1 if k >= 0 else lo


def tail_users(remote, *, minutes: float, max_bytes: int, local_now: float | None = None, sleep=time.sleep) -> dict[str, Any]:
    """Every user in the log's last `minutes` by the pod's own clock (`pod_time`: the clock that stamps the lines, so a skew here cannot move the
    window, and a log that has stopped shows as an old newest line, `newest_line_age_s`), read in one bounded tail read of each line's head (any user,
    so one no slot map names is seen too). Then a second stat after SETTLE_S: lines appended meanwhile are read too, and a third stat after that read
    checks nothing changed under it. A log replaced or shrunk, or a line still partial at the second stat, is a problem (the caller says INCONCLUSIVE)."""
    if not minutes > 0:
        raise ValueError(f"--minutes must be positive, not {minutes}")
    st = remote.stat()
    lo = max(0, st.size - max_bytes)
    if lo > 0:
        head = remote.read_range(lo, 65536)
        i = head.find(b"\n")
        if i < 0:
            raise RuntimeError(f"no line start within 64 KiB of byte {lo}")
        lo += i + 1
    hi = _cut(remote, lo, st.size)
    pod_now = remote.pod_time()
    first = parse_ts(remote.read_range(lo, 64)) if hi > lo else None
    heads = remote.read_heads(lo, hi) if hi > lo else b""
    sleep(SETTLE_S)
    st2 = remote.stat()
    problems = []
    if st2.inode != st.inode or st2.size < st.size:
        problems.append(f"the log changed during the check (inode {st.inode} -> {st2.inode}, size {st.size} -> {st2.size})")
    else:
        hi2 = _cut(remote, hi, st2.size)
        if hi2 > hi:
            heads += remote.read_heads(hi, hi2)
        if hi2 < st2.size:
            problems.append(f"a line was partial at the second stat (bytes {hi2}..{st2.size})")
        st3 = remote.stat()
        if st3.inode != st.inode or st3.size < st2.size:
            problems.append(f"the log changed during the check (inode {st.inode} -> {st3.inode}, size {st2.size} -> {st3.size})")
    stamped = []
    for ln in heads.splitlines():
        t, m = parse_ts(ln), _HEAD.match(ln)
        if t is not None and m is not None:
            stamped.append((t, m.group(1).decode()))
    newest = max((t for t, _ in stamped), default=None)
    now_site_g = pod_now
    since = now_site_g - minutes * 60
    seen: dict[str, dict] = {}
    for t, u in stamped:
        if t >= since:
            d = seen.setdefault(u, {"lines": 0, "first": t, "last": t})
            d["lines"] += 1
            d["first"], d["last"] = min(d["first"], t), max(d["last"], t)
    local_now = time.time() if local_now is None else local_now
    return {"size": st.size, "inode": st.inode, "from_off": lo, "to_off": hi, "first_line_ts": first, "now_site_g": now_site_g, "since": since,
            "local_minus_site_g_s": round(local_now - now_site_g, 3), "newest_line_age_s": round(now_site_g - newest, 3) if newest is not None else None,
            "problems": problems,
            "covered": first is not None and since is not None and first <= since - COVER_SLACK_S, "users": seen}


def verdict(tail: dict, held: list[str] | None, exclude: Sequence[str], slot_map: dict[str, dict], owner: dict[str, str]) -> tuple[int, dict]:
    key_of = {v["user"]: k for k, v in slot_map.items()}
    allowed = set(held or []) | set(exclude)
    left = []
    for u, d in sorted(tail["users"].items()):
        k = key_of.get(u)
        if k is not None and k in allowed:
            continue
        left.append({"user": u, "slot_key": k, "owner": owner.get(k, "unknown") if k else "not a slot user", **d})
    out = {"window_min": round((tail["now_site_g"] - tail["since"]) / 60, 2), "window_end_site_g": tail["now_site_g"], "local_minus_site_g_s": tail["local_minus_site_g_s"],
           "newest_line_age_s": tail["newest_line_age_s"], "covered": tail["covered"], "first_line_ts": tail["first_line_ts"],
           "read_bytes": tail["to_off"] - tail["from_off"], "held_on_23": held, "excluded": sorted(exclude), "problems": tail["problems"],
           "seen": {key_of.get(u, f"user {u} (no slot)"): d["lines"] for u, d in sorted(tail["users"].items())}, "not_accounted_for": left}
    if held is None:
        out["result"] = "INCONCLUSIVE: .23's leases could not be read"
        return 3, out
    if tail["problems"]:
        out["result"] = "INCONCLUSIVE: " + "; ".join(tail["problems"])
        return 3, out
    if not tail["covered"]:
        out["result"] = "INCONCLUSIVE: the tail read does not reach back past the window's start (raise --max-bytes)"
        return 3, out
    if left:
        out["result"] = "NOT SOLO: " + "; ".join(f"{x['slot_key'] or x['user']} ({x['owner']}): {x['lines']} line(s)" for x in left)
        return 2, out
    age = tail["newest_line_age_s"]
    out["result"] = "SOLO: no user outside .23's leases and the excluded keys in the window" + (
        f" (the log's newest line is {age:.0f} s old by site_g's clock: nothing at all was logged in the window)" if age is not None and age > tail["now_site_g"] - tail["since"] else "")
    return 0, out


def run_23(cmd: str, run: Callable | None = None, timeout: int = 60) -> str:
    import os
    import subprocess
    r = (run or subprocess.run)([*SSH_23, cmd], capture_output=True, timeout=timeout, env={**os.environ, "SSH_AUTH_SOCK": ""})
    if r.returncode != 0:
        raise RuntimeError(f".23 lease read: ssh exit {r.returncode}: {(r.stderr or b'')[-300:]!r}")
    return r.stdout.decode() if isinstance(r.stdout, bytes) else r.stdout


def dumps(code: int, out: dict) -> str:
    return json.dumps({"exit": code, **out}, indent=1, sort_keys=True)
