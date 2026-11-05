"""The audit log of one of B's providers (`site_u`, `site_x`, `site_o`, `site_p`), pulled across its rotations.

The log is `/var/log/op_worker/file_access_audit.log` in pod `oneprovider-0`. The infra session rotates it by renaming it to `file_access_audit.log.<UTC time>`
(a rotated name never changes again) and op_worker reopens a fresh file by itself, so a pull that followed one name would lose or double lines. This one:

- follows files by INODE, one ledger each (`<store>/f0001`, `f0002`, ...), and a registry `<store>/provider.json` in the order the files were met;
- finishes a rotated file before it reads the next one. A rotated file is finished when it is read to its end and the new live file has lines, or the file has
  had no write for `SETTLE_S` (the pod's clock against the file's ctime, which a rename and every write move); a rotated file that then grows is a gap;
- treats loss as a gap row in that file's ledger (a rotated file grown after it was finished, a file gone before it was finished, a live file replaced
  without a rename, a truncation, a torn last line), and a gap blocks the marker; a race at the live name (renamed between our stat and our read) is NOT a gap
  and writes nothing: the next cycle reads the rotated file whole, by its rotated name;
- tells the pod how far it has pulled: `<pod dir>/pulled-up-to`, one line `<ISO UTC> <last complete rotated file name>`, written by temp file and `mv`, read
  back, only forward, never naming the live file, and only over a prefix of files that are all finished and gap-free. The infra helper gzips rotated files up to
  that name and deletes the `.gz` seven days later, so this is the one write whose mistake destroys data;
- filters at the source to B's slot users (their audit-log user IDs, an allowlist; the log does not carry names), less an exclusion list (the infra test user).

`segments` gives `extract` the capture in the shape the site_g store's does. Nothing here writes to a pod but the marker.
"""
from __future__ import annotations

import contextlib
import copy
import datetime as dt
import fcntl
import hashlib
import itertools
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from .ledger import Ledger, LedgerError
from .pull import PullRefused, _cut, parse_ts
from .remote import AUDIT_DIR, MAX_RANGE, USER_FIELD, DskRemote, check_n, check_off, check_span

LIVE = "file_access_audit.log"
MARKER = "pulled-up-to"
SETTLE_S = 10.0
SCHEMA = "provider/1"
_NAME = re.compile(r"file_access_audit\.log(?:\.[A-Za-z0-9._:+-]+)?")
_WORD = re.compile(r"[A-Za-z0-9._-]+")            # an id or a name in a filter (a hyphen: `infra-rotation-test-after`); safe inside single quotes
_MARK = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ file_access_audit\.log\.[A-Za-z0-9._:+-]+")
_RC = re.compile(r"^ICSA_PULL_RC=(\d+)$")
_NICE = "nice -n 19 ionice -c3 "
_DIR = re.compile(r"/[A-Za-z0-9._/-]*")


def _check_name(name: str) -> str:
    if not isinstance(name, str) or not _NAME.fullmatch(name):
        raise ValueError(f"{name!r} is not a name of the audit log or one of its rotations")
    return name


def _ere(word: str) -> str:
    return word.replace(".", r"\.")


@dataclass(frozen=True)
class UserFilter:
    """Whose lines to keep: the `user: <id>;` field of the line (anchored at its start, never a path) is one of `users`, or begins with one of `prefixes`
    (the field's characters to its `;`), and is none of `exclude`. At least one of `users` and `prefixes`; an empty filter would read nothing or everything."""
    users: tuple[str, ...] = ()
    prefixes: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()

    def __post_init__(self):
        for f in ("users", "prefixes", "exclude"):
            vals = getattr(self, f)
            if isinstance(vals, (str, bytes)) or not all(isinstance(v, str) and _WORD.fullmatch(v) for v in vals):
                raise ValueError(f"{f}: ids and names are letters, digits, '.', '_' and '-' only")
            object.__setattr__(self, f, tuple(sorted(set(vals))))
        if not self.users and not self.prefixes:
            raise ValueError("a filter needs at least one user or prefix to allow")

    def sha(self) -> str:
        return hashlib.sha256(json.dumps([self.users, self.prefixes, self.exclude]).encode()).hexdigest()[:16]

    def _alts(self, words, prefix_words=()) -> str:
        return "|".join([*(_ere(w) for w in words), *(_ere(w) + "[A-Za-z0-9._-]*" for w in prefix_words)])

    def allow_ere(self) -> str:
        return self._alts(self.users, self.prefixes)

    def exclude_ere(self) -> str:
        return self._alts(self.exclude)

    def regexes(self) -> tuple[re.Pattern, re.Pattern | None]:
        """The same two tests as the pod's two greps, in Python (bytes): (allow, exclude or None)."""
        head = USER_FIELD.encode().replace(b"[^]]", rb"[^\]]")
        alts = [re.escape(w).encode() for w in self.users] + [re.escape(w).encode() + rb"[A-Za-z0-9._-]*" for w in self.prefixes]
        allow = re.compile(head + b"(?:" + b"|".join(alts) + b");")
        excl = re.compile(head + b"(?:" + b"|".join(re.escape(w).encode() for w in self.exclude) + b");") if self.exclude else None
        return allow, excl


@dataclass(frozen=True)
class LogFile:
    name: str
    inode: int
    size: int
    ctime: float          # the last write or rename, as the pod's stat says (whole seconds, rounded up to the end of the second: never earlier than it was)


# ---------------------------------------------------------------- the remotes
class LocalDirRemote:
    """The reference: a local directory read the way the pod reads its own. `skew` moves the pod's clock on, so a test can let ten seconds pass."""

    def __init__(self, directory, skew: float = 0.0):
        self.dir, self.skew = Path(directory), skew

    def list_files(self) -> list[LogFile]:
        out = []
        for n in sorted(os.listdir(self.dir)):
            if _NAME.fullmatch(n):
                st = os.stat(self.dir / n)
                out.append(LogFile(n, st.st_ino, st.st_size, st.st_ctime))
        return out

    def stat(self, name: str) -> LogFile | None:
        _check_name(name)
        try:
            st = os.stat(self.dir / name)
        except FileNotFoundError:
            return None
        return LogFile(name, st.st_ino, st.st_size, st.st_ctime)

    def pod_time(self) -> float:
        return time.time() + self.skew

    def _read(self, name: str, off: int, n: int) -> bytes:
        with open(self.dir / _check_name(name), "rb") as f:
            f.seek(off)
            return f.read(n)

    def read_range(self, name: str, off: int, n: int) -> bytes:
        return self._read(name, check_off(off), check_n(n))

    def read_filtered(self, name: str, off: int, end: int, flt: UserFilter) -> bytes:
        off, end = check_span(off, end)
        if off and self._read(name, off - 1, 1) != b"\n":
            raise ValueError(f"off {off} is not a line start")
        data = self._read(name, off, end - off)
        if len(data) != end - off:
            raise ValueError(f"end {end} is beyond the end of the file")
        if data and data[-1:] != b"\n":
            raise ValueError(f"end {end} is not a line start")
        allow, excl = flt.regexes()
        return b"".join(ln + b"\n" for ln in data.split(b"\n")[:-1] if allow.search(ln) and not (excl and excl.search(ln)))

    def read_marker(self) -> str | None:
        p = self.dir / MARKER
        return p.read_text().rstrip("\n") if p.is_file() else None

    def write_marker(self, line: str) -> None:
        _check_marker(line)
        tmp = self.dir / f".{MARKER}.tmp"
        tmp.write_text(line + "\n")
        os.replace(tmp, self.dir / MARKER)


def _check_marker(line: str) -> str:
    if not isinstance(line, str) or not _MARK.fullmatch(line):
        raise ValueError(f"not a marker line (`<ISO UTC> <rotated file name>`): {line!r}")
    return line


class PodDirRemote(DskRemote):
    """The same through `kubectl exec` into `oneprovider-0` of namespace `namespace` with the audit reader's kubeconfig. The kubeconfig's path goes in the
    child's environment (KUBECONFIG), never on a command line, in a log or in a message; only the context's name is in the command. Every name and every
    filter word is validated before a command string exists. Reuses DskRemote's status-line, gzip and truncation checks: a failed `dd` or a cut reply is an
    error, never an empty read."""

    def __init__(self, namespace: str, *, kubeconfig, context: str = "icsa-audit-reader", directory: str = AUDIT_DIR, exec_prefix: str | None = None,
                 run: Callable | None = None, timeout_s: int = 600, ionice: bool = True, pod_gzip: bool = False):
        if not re.fullmatch(r"[a-z0-9-]+", namespace) or not re.fullmatch(r"[A-Za-z0-9._@:-]+", context):
            raise ValueError("a namespace or context name that is not a plain name")
        if not _DIR.fullmatch(directory) or ".." in directory.split("/"):
            raise ValueError(f"{directory!r}: not a plain absolute path")
        ex = exec_prefix if exec_prefix is not None else f"kubectl --context {context} -n {namespace} exec oneprovider-0 --"
        super().__init__(timeout_s=timeout_s, run=run, ionice=ionice, pod_gzip=pod_gzip, path=f"{directory}/{LIVE}", exec_prefix=ex, transport="dsk")
        self.namespace, self.kubeconfig = namespace, str(kubeconfig)

    def _argv(self, cmd: str) -> list[str]:
        return ["bash", "-c", cmd]

    def _env(self) -> dict[str, str]:
        return {**os.environ, "KUBECONFIG": self.kubeconfig, "SSH_AUTH_SOCK": ""}

    def _view(self, name: str) -> "PodDirRemote":
        v = copy.copy(self)
        v.path, v.name = f"{self.dir}/{_check_name(name)}", name
        return v

    def list_files(self) -> list[LogFile]:
        cmd = f"{self.ex} sh -c \"cd {self.dir} && stat -c '%i %s %Z %n' {LIVE}*; echo ICSA_PULL_RC=\\$?\""
        out = []
        for ln in self._lines_rc(self._call(cmd, "list_files"), "list_files"):
            m = re.fullmatch(r"(\d+) (\d+) (\d+) (\S+)", ln)
            if m is None or not _NAME.fullmatch(m[4]):
                raise RuntimeError(f"list_files: unexpected line {ln[:80]!r}")
            out.append(LogFile(m[4], int(m[1]), int(m[2]), float(m[3]) + 1.0))
        if not out:                                       # no live file is normal right after a rotation (op_worker opens the fresh one on its next line); no file at all is not
            raise RuntimeError(f"list_files: no {LIVE}* in {self.dir}: is the log on, and did it move?")
        return out

    def stat(self, name: str) -> LogFile | None:
        _check_name(name)
        return next((f for f in self.list_files() if f.name == name), None)

    def read_range(self, name: str, off: int, n: int) -> bytes:
        return DskRemote.read_range(self._view(name), off, n)

    def read_filtered(self, name: str, off: int, end: int, flt: UserFilter) -> bytes:
        off, end = check_span(off, end)
        v = self._view(name)
        if end == off:
            return b""
        nice = _NICE if self.ionice else ""
        grep = f"{nice}grep -aE '^ICSA_DD_RC=|{USER_FIELD}({flt.allow_ere()});'"
        if flt.exclude:
            grep += f" | {nice}grep -avE '{USER_FIELD}({flt.exclude_ere()});'"
        inner = f"{{ {v._dd(off, end - off)}; r=\\$?; echo; echo ICSA_DD_RC=\\$r; }} | {grep}; echo ICSA_PULL_RC=\\$?"
        body = self._gunzip(self._call(self._gz(inner, None), "read_filtered"), "read_filtered")
        m = re.search(rb"(?:^|\n)ICSA_DD_RC=(\d+)\nICSA_PULL_RC=(\d+)\n\Z", body)
        if m is None:
            raise RuntimeError("read_filtered: no exit status came back from the remote read (a dead transport?)")
        if m.group(1) != b"0":
            raise RuntimeError(f"read_filtered: dd exit {m.group(1).decode()}")
        if m.group(2) not in (b"0", b"1"):
            raise RuntimeError(f"read_filtered: grep exit {m.group(2).decode()}")
        return body[:m.start() + 1] if body[m.start():m.start() + 1] == b"\n" else body[:m.start()]

    def read_marker(self) -> str | None:
        cmd = f'{self.ex} sh -c "if [ -f {self.dir}/{MARKER} ]; then cat {self.dir}/{MARKER}; else echo ICSA_NO_MARKER; fi; echo ICSA_PULL_RC=\\$?"'
        lines = self._lines_rc(self._call(cmd, "read_marker"), "read_marker")
        return None if lines == ["ICSA_NO_MARKER"] else "\n".join(lines)

    def write_marker(self, line: str) -> None:
        _check_marker(line)
        tmp = f"{self.dir}/.{MARKER}.tmp"
        cmd = f"{self.ex} sh -c \"printf '%s\\n' '{line}' > {tmp} && mv {tmp} {self.dir}/{MARKER}; echo ICSA_PULL_RC=\\$?\""
        self._lines_rc(self._call(cmd, "write_marker"), "write_marker")


# ---------------------------------------------------------------- the registry
def _iso(t: float) -> str:
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _save(path: Path, obj: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, sort_keys=True))
    os.replace(tmp, path)


def _load(store: Path) -> dict | None:
    p = store / "provider.json"
    return json.loads(p.read_text()) if p.is_file() else None


class _Named:
    """One file of the remote as `pull._cut` wants it: read_range(off, n)."""

    def __init__(self, remote, name: str):
        self.remote, self.name = remote, name

    def read_range(self, off: int, n: int) -> bytes:
        return self.remote.read_range(self.name, off, n)


@contextlib.contextmanager
def store_lock(store):
    """One cycle at a time on a store (a daemon and a manual run would otherwise pick the same chunk number and overwrite a captured chunk the pod has been told
    it may delete). A second raises instead of waiting."""
    store = Path(store)
    store.mkdir(parents=True, exist_ok=True)
    fd = os.open(store / "provider.lock", os.O_CREAT | os.O_RDWR, 0o644)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise LedgerError(f"{store}: another pull holds the store") from None
        yield
    finally:
        os.close(fd)


def _gap(ledger: Ledger, entry: dict, reason: str, pulled: float, report: dict) -> None:
    ledger.append_gap(entry["inode"], ledger.offset() or 0, reason, pulled)
    entry.setdefault("gaps", []).append(reason)
    report["gaps"].append({"n": entry["n"], "reason": reason})


def _pull_file(remote, entry: dict, ledger: Ledger, flt: UserFilter, pulled: float, max_bytes: int, report: dict):
    """One read of one file. (status, stat, to_off): status ok | race (nothing written) | gone | refused (a gap row says why)."""
    name, prev = entry["name"], ledger.last_pull()
    off = prev["to_off"] if prev else 0
    st = remote.stat(name)
    if st is None:
        if name == LIVE:       # renamed after our listing, and op_worker has not opened a fresh live file yet: a race. The inode is there under its rotated name; the next
            report["races"] += 1   # listing reconciles it, and a live file that really vanished is found there (gone before it was finished), never guessed here
            return "race", None, off
        return "gone", None, off
    if st.inode != entry["inode"]:
        if name == LIVE:                                           # renamed between our listing and now: the next listing sees it
            report["races"] += 1
            return "race", st, off
        _gap(ledger, entry, f"the rotated name {name} now holds inode {st.inode}, not {entry['inode']}", pulled, report)
        return "refused", st, off
    if st.size < off:
        _gap(ledger, entry, f"the size {st.size} is below the offset {off}: the file was truncated", pulled, report)
        return "refused", st, off
    if prev is not None and prev.get("size_at") is not None and st.size < prev["size_at"]:
        _gap(ledger, entry, f"the file shrank: the last pull saw {prev['size_at']} bytes, now {st.size}", pulled, report)
        return "refused", st, off
    if st.size == off:                                             # nothing new: coverage moves on a quiet log
        ledger.append_pull(inode=st.inode, from_off=off, to_off=off, size_at=st.size, pulled_utc=pulled, data=b"", complete=True, users_sha=flt.sha())
        return "ok", st, off
    try:
        e = _cut(_Named(remote, name), off, min(st.size, off + max_bytes))
    except PullRefused as ex:
        _gap(ledger, entry, str(ex), pulled, report)
        return "refused", st, off
    if e is None:
        swapped = remote.stat(name)
        if name == LIVE and (swapped is None or swapped.inode != st.inode):          # the cut's read landed on a file renamed under us: a race, not a shrinkage
            report["races"] += 1
            return "race", st, off
        _gap(ledger, entry, "a read at the cut came back short: the file shrank during the pull", pulled, report)
        return "refused", st, off
    if e == off:                                                   # only half a line after the offset: wait for its end
        return "ok", st, off
    try:
        data = remote.read_filtered(name, off, e, flt)
    except ValueError:                                             # a strict remote refuses a span that is not whole lines: if the file was swapped under us, a race
        swapped = remote.stat(name)
        if name == LIVE and (swapped is None or swapped.inode != st.inode):
            report["races"] += 1
            return "race", st, off
        raise
    after = remote.stat(name)
    if after is None or after.inode != st.inode:
        if name == LIVE:
            report["races"] += 1
            return "race", st, off
        _gap(ledger, entry, f"the file {name} changed during the read (inode {st.inode} -> {after.inode if after else None})", pulled, report)
        return "refused", st, off
    if after.size < e:
        _gap(ledger, entry, f"the file shrank during the read ({st.size} -> {after.size}); the bytes read are dropped", pulled, report)
        return "refused", st, off
    ledger.append_pull(inode=st.inode, from_off=off, to_off=e, size_at=st.size, pulled_utc=pulled, data=data, complete=e == st.size, users_sha=flt.sha())
    return "ok", st, e


def pull_cycle(remote, store, flt: UserFilter, *, provider: str, settle_s: float = SETTLE_S, max_bytes: int = 256 * 2 ** 20) -> dict:
    with store_lock(store):
        return _pull_cycle(remote, store, flt, provider=provider, settle_s=settle_s, max_bytes=max_bytes)


def _pull_cycle(remote, store, flt: UserFilter, *, provider: str, settle_s: float, max_bytes: int) -> dict:
    """One cycle: list the directory, follow the files by inode, read what is new in each (a rotated file to its end before the next file), finish what can
    be finished, and tell the pod how far the ledgers hold. Returns {provider, pulled_utc, files: [{n, name, inode, pulled, finished, to_off}], gaps, refused,
    races, marker (the line written this cycle, or None)}. The pod's clock stamps everything, the log's own and the pulls."""
    store = Path(store)
    store.mkdir(parents=True, exist_ok=True)
    reg = _load(store)
    if reg is None:
        reg = {"schema": SCHEMA, "provider": provider, "filter": {"users": list(flt.users), "prefixes": list(flt.prefixes), "exclude": list(flt.exclude)},
               "filter_sha": flt.sha(), "files": [], "marker": None, "covered_from": None, "pre_existing_gz": [], "pre_existing_marker": None, "created_utc": None}
        first = True
    else:
        first = False
        if reg["provider"] != provider or reg["filter_sha"] != flt.sha():
            raise ValueError(f"{store} follows {reg['provider']} with another filter: a changed filter would leave holes in the earlier span; start a new store")
    pulled = remote.pod_time()
    listing = remote.list_files()
    report: dict = {"provider": provider, "pulled_utc": pulled, "files": [], "gaps": [], "refused": [], "races": 0, "marker": None}
    if not listing or len([f for f in listing if f.name == LIVE]) > 1:
        raise RuntimeError(f"the listing holds {[f.name for f in listing][:6]}: not an audit log directory")
    gz = sorted(f.name for f in listing if f.name.endswith(".gz"))
    listed = [f for f in listing if not f.name.endswith(".gz")]
    if first:
        reg["created_utc"], reg["pre_existing_gz"], reg["pre_existing_marker"] = pulled, gz, remote.read_marker()
    files = reg["files"]
    match: dict[int, LogFile] = {}                      # entry n -> the listed file it is. By inode, but a FINISHED rotated file keeps its name for good: the same inode
    taken: set[str] = set()                             # number under another name is another file's (the number was freed when the helper gzipped the old one)
    for e in files:
        f = next((g for g in listed if g.inode == e["inode"]), None) if not e["lost"] else None
        if f is not None and not (e["finished"] and f.name != e["name"]):
            match[e["n"]] = f
            taken.add(f.name)
            if f.name != e["name"]:
                e["name"] = f.name
                e["names"].append(f.name)
    # new files, rotated ones by the order of their NAMES (the UTC time in them never changes; the ctime moves with every straggler's write), the live one last
    for f in sorted((f for f in listed if f.name not in taken), key=lambda f: (f.name == LIVE, "" if f.name == LIVE else f.name, f.ctime)):
        n = len(files) + 1
        files.append({"n": n, "dir": f"f{n:04d}", "inode": f.inode, "name": f.name, "names": [f.name], "first_seen_utc": pulled, "finished": False, "final_size": None,
                      "finished_utc": None, "lost": None, "gaps": []})
        match[n] = f
    if first and files:
        head = remote.read_range(files[0]["name"], 0, 4096)
        reg["covered_from"] = parse_ts(head) or pulled
    # ---- loss that has already happened
    for e in files:
        ledger = Ledger(store / e["dir"])
        f = match.get(e["n"])
        if f is None and not e["finished"] and not e["lost"]:
            e["lost"] = "gone"
            _gap(ledger, e, f"the file (inode {e['inode']}, last seen as {e['name']}) is gone before it was finished: its unread tail is lost", pulled, report)
        elif f is not None and e["finished"] and f.size > e["final_size"] and "grew" not in e:
            e["grew"] = True
            _gap(ledger, e, f"the rotated file {e['name']} grew after it was finished ({e['final_size']} -> {f.size} bytes): a straggler wrote into it", pulled, report)
    # ---- the pulls, in order: a file only when the one before it is finished
    prev_done = True
    for i, e in enumerate(files):
        row = {"n": e["n"], "name": e["name"], "inode": e["inode"], "pulled": False, "finished": e["finished"], "to_off": None}
        report["files"].append(row)
        if e["finished"] or e["lost"]:
            continue
        if not prev_done:
            break
        ledger = Ledger(store / e["dir"])
        status, st, to_off = _pull_file(remote, e, ledger, flt, pulled, max_bytes, report)
        if status == "gone":
            e["lost"] = "gone"
            _gap(ledger, e, f"the file {e['name']} is gone before it was finished: its unread tail is lost", pulled, report)
            continue
        if status == "refused":
            report["refused"].append({"n": e["n"], "name": e["name"]})
            break
        if status == "race":
            break
        row["pulled"] = True
        last = ledger.last_pull()
        row["to_off"] = last["to_off"] if last else to_off
        rotated = e["name"] != LIVE
        if rotated:
            fin = remote.stat(e["name"])                         # the size AFTER the read: what we acknowledge must be what is there now
            later = {x["n"] for x in files[i + 1:]}
            moved_on = any(g.size > 0 for n, g in match.items() if n in later)
            quiet = fin is not None and pulled - fin.ctime >= settle_s
            if fin is not None and fin.inode == e["inode"] and (quiet or moved_on):
                if fin.size == row["to_off"]:
                    e["finished"], e["final_size"], e["finished_utc"], row["finished"] = True, fin.size, pulled, True
                elif fin.size > row["to_off"]:
                    rest = remote.read_range(e["name"], row["to_off"], min(fin.size - row["to_off"], MAX_RANGE))
                    if b"\n" not in rest and fin.size - row["to_off"] <= MAX_RANGE:      # no line end in what is left: a torn last line, not a bounded read
                        _gap(ledger, e, f"torn tail: {fin.size - row['to_off']} bytes after the last line end of a rotated file", pulled, report)
                        e["finished"], e["final_size"], e["finished_utc"], row["finished"] = True, fin.size, pulled, True
        prev_done = e["finished"] or not rotated
        _save(store / "provider.json", reg)
    # ---- the marker: a finished, gap-free prefix of files, forward only, never the live file, and never over a rotated name the pod lists that we do not hold
    clean = {e["name"] for e in files if e["finished"] and not e["lost"] and not e.get("gaps") and not Ledger(store / e["dir"]).gaps() and e["name"] != LIVE}
    held = {e["name"] for e in files if e["name"] != LIVE} | {f.name for f in listed if f.name != LIVE}
    target = None
    for name in sorted(held):                                  # by NAME, the order the helper's "through <name>" takes: every rotated file up to the target is ours and clean
        if name not in clean:
            break
        target = name
    if target is not None and (reg["marker"] is None or target > reg["marker"]["name"]):
        cur = remote.read_marker()
        cur_name = cur.split(" ", 1)[1] if cur and " " in cur else None
        if cur_name is None or cur_name < target:              # never move the pod's marker back, and never rewrite what it says already
            line = f"{_iso(pulled)} {target}"
            remote.write_marker(line)
            back = remote.read_marker()
            if back != line:
                raise RuntimeError(f"the marker was written as {line!r} and read back as {back!r}")
            reg["marker"] = {"name": target, "line": line}
            report["marker"] = line
    _save(store / "provider.json", reg)
    return report


# ---------------------------------------------------------------- what extract reads
def segments(root) -> dict:
    """The capture as `extract` reads it: the files' lines in order, from the first line of the first file we met. `covered_until` is the last complete pull of
    the live file, and only while every file before it is finished: otherwise None, and every run is `capture_incomplete`, never credited."""
    root = Path(root)
    reg = _load(root)
    if reg is None:
        raise SystemExit(f"no provider registry at {root / 'provider.json'}: start the pull")
    files = reg["files"]
    ledgers = [Ledger(root / e["dir"]) for e in files]
    closed = all(e["finished"] or e["lost"] for e in files[:-1])

    def lines():
        return itertools.chain.from_iterable(lg.iter_lines() for lg in ledgers)
    return {"joined": True, "covered_from": reg["covered_from"], "lines": lines, "covered_until": ledgers[-1].covered_until() if ledgers and closed else None,
            "gaps": [g for lg in ledgers for g in lg.gaps()],
            "provenance": {"provider": reg["provider"], "files": [{"n": e["n"], "inode": e["inode"], "name": e["name"], "finished": e["finished"], "lost": e["lost"],
                                                                   "offset": lg.offset()} for e, lg in zip(files, ledgers)]}}
