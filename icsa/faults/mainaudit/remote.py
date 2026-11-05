"""site_g's audit log as the M audit reader sees it: `stat`, the rotated siblings, two byte-bounded reads, and the pre-flight's probes.

`LocalFileRemote` is the reference (the tests' fake): the same semantics over a local file, and strict, so a read that does not start and end on
a line start fails there. `DskRemote` only builds command strings and runs them, by one of two transports: "site_g-direct" (ssh to site_g's node over the tailnet, then the node's
`sudo -n k3s kubectl exec` into the pod; the lead's path of 4 Nov, which keeps the pod's output off Azure's WAN) or "dsk" (`day0/scripts/dsk.sh`
through data-site_ay, as calibrate.py:545,575-599,722-747 do). The filter runs inside the pod; gzip in the pod (`pod_gzip`) or on the host in between.

Two traps the commands close, both silent otherwise (silent-fallback-hazards.md, A and B):
- `dd | grep` reports grep's exit status, so a failed dd (an `iflag` the pod's dd lacks) reads as "no line matched" and the offset advances over
  data nobody read. dd's own status travels in-band as an `ICSA_DD_RC=` line that grep also passes, and it must be 0.
- every id and offset is validated before any command string exists: `re.fullmatch` (not `$`, which accepts a trailing newline) and exact ints (not bool).
"""
from __future__ import annotations

import gzip
import os
import re
import shlex
import subprocess
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol, Sequence

REPO = Path(__file__).resolve().parents[3]
AUDIT_DIR, AUDIT_NAME = "/var/log/op_worker", "file_access_audit.log"
OP_EXEC = "kubectl --kubeconfig ~/.kube/site_g-config -n oneprovider-site_g exec oneprovider-0 --"      # calibrate._OP_EXEC; a test pins the two together
# The direct path to site_g's node (the lead, 4 Nov): ssh from this host over the tailnet, then k3s's own kubectl on the node, so the pod's output never crosses
# Azure's WAN (dsk.sh goes through data-site_ay in Azure). `sudo -n`: fail at once rather than wait for a password nobody can type. The log's real path in the
# pod; /var/log/op_worker is a symlink to its directory.
SITE_G_DIRECT_HOST = "email-4@example"
SITE_G_DIRECT_SSH = ("ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", "-o", "ProxyCommand=none", "-o", "IdentitiesOnly=yes",
                 "-i", "~/.secrets/icsa-2027/runvm_ed25519", "-o", "UserKnownHostsFile=~/.secrets/icsa-2027/runvm_known_hosts", SITE_G_DIRECT_HOST)
SITE_G_DIRECT_EXEC = "sudo -n k3s kubectl -n oneprovider-site_g exec oneprovider-0 --"
SITE_G_DIRECT_PATH = "/volumes/persistence/var/log/op_worker/file_access_audit.log"
TRANSPORTS = ("site_g-direct", "dsk")
MAX_RANGE = 65536
POD_TOOLS = ("dd", "grep", "stat", "ls", "sh", "nice", "ionice", "gzip")          # the pod's gzip is reported as "gzip_pod"; "gzip" is the dsk host's
TOOLS = ("dd", "grep", "stat", "ls", "sh", "nice", "ionice", "gzip", "gzip_pod")
_ID = re.compile(r"[A-Za-z0-9]+")
_RC = re.compile(r"^ICSA_PULL_RC=(\d+)$")
_NICE = "nice -n 19 ionice -c3 "


@dataclass(frozen=True)
class FileStat:
    inode: int
    size: int


class Remote(Protocol):
    def stat(self) -> FileStat: ...
    def siblings(self) -> list[str]:
        """Other names in the log's directory that start with the log's name (rotated files)."""
    def read_range(self, off: int, n: int) -> bytes:
        """Up to n raw bytes at off (fewer only at the end of the file), n <= 65536: cut points and bisection."""
    def read_filtered(self, off: int, end: int, users: Sequence[str]) -> bytes:
        """The whole lines in [off, end) whose `user: <id>;` field is one of users. The caller guarantees off and end are line starts."""
    def tools(self) -> dict[str, bool]: ...
    def timed_read(self, off: int, n: int) -> tuple[float, int]:
        """Read n bytes at off and return (seconds in the pod, bytes read): the count only, never the content."""


def check_users(users) -> tuple[str, ...]:
    """Sorted, site_f-duplicated ids; ValueError on anything but a non-empty list of alphanumeric strings. Slot users of any option may go in."""
    if isinstance(users, (str, bytes)) or not users:
        raise ValueError("a user filter needs a non-empty list of ids")
    for u in users:
        if not isinstance(u, str) or not _ID.fullmatch(u):
            raise ValueError(f"user id {u!r} is not alphanumeric")
    return tuple(sorted(set(users)))


def check_off(x, what: str = "offset") -> int:
    if type(x) is not int or x < 0:           # bool and float are refused: they would format into a command as True / 1.0
        raise ValueError(f"{what} must be a non-negative int, not {x!r}")
    return x


def check_n(n) -> int:
    if type(n) is not int or not 1 <= n <= MAX_RANGE:
        raise ValueError(f"a ranged read is 1..{MAX_RANGE} bytes, not {n!r}")
    return n


def check_span(off, end) -> tuple[int, int]:
    check_off(off, "off"), check_off(end, "end")
    if end < off:
        raise ValueError(f"end {end} is before off {off}")
    return off, end


def _pattern(users: Sequence[str]) -> str:
    return "|".join(check_users(users))


# The user field of a log line, anchored at the line start: `[ts] request: <req>; user: <id>;`. Unanchored, `user: <id>;` also matches inside a path or a request
# name and the line would be kept as that user's. The grep (ERE, in single quotes in the command) and the local regex are the same pattern.
USER_FIELD = r"^\[[^]]*\] request: [^;]*; user: "


class LocalFileRemote:
    """The reference: a local file read the way the pod's dd and grep read site_g's. `siblings` are added to the directory's own."""

    def __init__(self, path, siblings: Sequence[str] = ()):
        self.path, self._sib = Path(path), tuple(siblings)

    def stat(self) -> FileStat:
        st = os.stat(self.path)
        return FileStat(st.st_ino, st.st_size)

    def siblings(self) -> list[str]:
        real = {n for n in os.listdir(self.path.parent) if n != self.path.name and n.startswith(self.path.name)}
        return sorted(real | set(self._sib))

    def _read(self, off: int, n: int) -> bytes:
        with open(self.path, "rb") as f:
            f.seek(off)
            return f.read(n)

    def read_range(self, off: int, n: int) -> bytes:
        return self._read(check_off(off), check_n(n))

    def read_filtered(self, off: int, end: int, users: Sequence[str]) -> bytes:
        off, end = check_span(off, end)
        pat = re.compile(USER_FIELD.encode().replace(b"[^]]", rb"[^\]]") + b"(" + _pattern(users).encode() + b");")
        if off and self._read(off - 1, 1) != b"\n":
            raise ValueError(f"off {off} is not a line start")
        data = self._read(off, end - off)
        if len(data) != end - off:
            raise ValueError(f"end {end} is beyond the end of the file")
        if data and data[-1:] != b"\n":
            raise ValueError(f"end {end} is not a line start")
        return b"".join(ln + b"\n" for ln in data.split(b"\n")[:-1] if pat.search(ln))

    def pod_time(self) -> float:
        import time
        return time.time()

    def read_heads(self, off: int, end: int) -> bytes:
        off, end = check_span(off, end)
        pat = re.compile(USER_FIELD.encode().replace(b"[^]]", rb"[^\]]") + rb"[A-Za-z0-9]*;")
        data = self._read(off, end - off)
        if len(data) != end - off or (data and data[-1:] != b"\n") or (off and self._read(off - 1, 1) != b"\n"):
            raise ValueError(f"[{off}, {end}) is not a span of whole lines")
        return b"".join(m.group(0) + b"\n" for ln in data.split(b"\n")[:-1] if (m := pat.match(ln)))

    def tools(self) -> dict[str, bool]:
        return {k: True for k in TOOLS}

    def timed_read(self, off: int, n: int) -> tuple[float, int]:
        import time
        t = time.monotonic()
        got = len(self._read(check_off(off), check_n_big(n)))
        return time.monotonic() - t, got


def check_n_big(n) -> int:
    if type(n) is not int or n < 1:
        raise ValueError(f"a timed read is at least 1 byte, not {n!r}")
    return n


class DskRemote:
    """Commands for `bash dsk.sh "<kubectl exec ... sh -c ...>"`. `run` is called as run(argv, capture_output=True, timeout=, env=) and returns an object with
    returncode, stdout (bytes) and stderr; it defaults to subprocess.run, looked up at call time. `dry_run` never calls it. `ionice` puts
    `nice -n 19 ionice -c3` in front of dd and grep in the pod: pass what `tools()` found, since a pod without ionice fails the whole read.
    `pod_gzip` compresses inside the pod (`gzip -1`, nothing on the dsk host), so the WAN between the pod and data-site_ay carries the compressed bytes;
    False gzips on the dsk host. Either way the reply is decompressed here and the status lines and truncation are checked as before."""

    def __init__(self, dsk: str | Path = "day0/scripts/dsk.sh", timeout_s: int = 600, *, dry_run: bool = False, run: Callable | None = None,
                 ionice: bool = True, pod_gzip: bool = False, path: str | None = None, exec_prefix: str | None = None, transport: str = "dsk"):
        """`transport`: "dsk" (dsk.sh through data-site_ay, the default here) or "site_g-direct" (ssh to site_g's node and its k3s kubectl; the CLI's default)."""
        if transport not in TRANSPORTS:
            raise ValueError(f"transport {transport!r}: one of {TRANSPORTS}")
        p = Path(dsk)
        self.dsk, self.timeout_s, self.dry_run, self.ionice, self.pod_gzip = (p if p.is_absolute() else REPO / p), timeout_s, dry_run, ionice, pod_gzip
        direct = transport == "site_g-direct"
        self.transport = transport
        self._run = run
        self.path = path if path is not None else (SITE_G_DIRECT_PATH if direct else f"{AUDIT_DIR}/{AUDIT_NAME}")
        self.ex = exec_prefix if exec_prefix is not None else (SITE_G_DIRECT_EXEC if direct else OP_EXEC)
        self.dir, self.name = os.path.split(self.path)

    def _argv(self, cmd: str) -> list[str]:
        return [*SITE_G_DIRECT_SSH, cmd] if self.transport == "site_g-direct" else ["bash", str(self.dsk), cmd]

    def _env(self) -> dict[str, str]:
        if self.transport == "site_g-direct":
            return {**os.environ, "SSH_AUTH_SOCK": ""}            # the local agent socket hangs on this host (dsk.sh unsets it too)
        return {**os.environ, "DSK_TIMEOUT": str(max(self.timeout_s - 20, 1))}

    # ---- the command strings (no I/O; the arguments are already validated, or are the placeholders of describe)
    def _dd(self, off, n) -> str:
        return f"{_NICE if self.ionice else ''}dd if={self.path} bs=1M iflag=skip_bytes,count_bytes skip={off} count={n} 2>/dev/null"

    def _c_tools(self) -> str:
        return (f'{self.ex} sh -c "for t in {" ".join(POD_TOOLS)}; do if command -v \\$t >/dev/null 2>&1; then echo TOOL_\\$t=1; else echo TOOL_\\$t=0; fi; done; '
                'echo ICSA_PULL_RC=\\$?"')

    def _c_tools_dsk(self) -> str:
        return "if command -v gzip >/dev/null 2>&1; then echo TOOL_gzip=1; else echo TOOL_gzip=0; fi; echo ICSA_PULL_RC=0"

    def _c_stat(self) -> str:
        return f'{self.ex} sh -c "stat -c \'%i %s\' {self.path}; echo ICSA_PULL_RC=\\$?"'

    def _c_ls(self) -> str:
        return f'{self.ex} sh -c "ls -1 {self.dir}; echo ICSA_PULL_RC=\\$?"'

    def _gz(self, inner: str, pod: bool | None) -> str:
        """`inner` is the shell text of the pod command; compress it in the pod (no gzip outside the quotes) or on the dsk host (gzip after them)."""
        if self.pod_gzip if pod is None else pod:
            return f'{self.ex} sh -c "{{ {inner}; }} | {"nice -n 19 " if self.ionice else ""}gzip -1 -c"'
        return f'{self.ex} sh -c "{inner}" | gzip -c'

    def _c_range(self, off, n, pod: bool | None = None) -> str:
        return self._gz(f"{{ {self._dd(off, n)}; r=\\$?; echo; echo ICSA_DD_RC=\\$r; }}", pod)

    def _c_filtered(self, off, end, alt, pod: bool | None = None) -> str:
        grep = f"{_NICE if self.ionice else ''}grep -aE '^ICSA_DD_RC=|{USER_FIELD}({alt});'"
        return self._gz(f'{{ {self._dd(off, "END-OFF" if end == "END" else end - off)}; r=\\$?; echo; echo ICSA_DD_RC=\\$r; }} | {grep}; echo ICSA_PULL_RC=\\$?', pod)

    def _c_heads(self, off, end, pod: bool | None = None) -> str:
        grep = f"{_NICE if self.ionice else ''}grep -aoE '^ICSA_DD_RC=[0-9]+|{USER_FIELD}[A-Za-z0-9]*;'"
        return self._gz(f'{{ {self._dd(off, "END-OFF" if end == "END" else end - off)}; r=\\$?; echo; echo ICSA_DD_RC=\\$r; }} | {grep}; echo ICSA_PULL_RC=\\$?', pod)

    def _c_date(self) -> str:
        return f'{self.ex} sh -c "date +%s.%N; echo ICSA_PULL_RC=\\$?"'

    def _c_timed(self, off, n) -> str:
        return (f'{self.ex} sh -c "t0=\\$(date +%s.%N); c=\\$({self._dd(off, n)} | wc -c); t1=\\$(date +%s.%N); '
                'echo ICSA_TIMED \\$t0 \\$t1 \\$c; echo ICSA_PULL_RC=0"')

    def describe(self, users: Sequence[str]) -> list[str]:
        """The command lines this remote would run, one `# what` line and one shell line each, with OFF, N and END standing for the numbers."""
        alt = _pattern(users)
        env = (f"SSH_AUTH_SOCK= {shlex.join(SITE_G_DIRECT_SSH)} " if self.transport == "site_g-direct"
               else f"DSK_TIMEOUT={max(self.timeout_s - 20, 1)} bash {shlex.quote(str(self.dsk))} ")
        cmds = [("tools in the pod", self._c_tools()), ("tools on the dsk host", self._c_tools_dsk()), ("stat", self._c_stat()), ("siblings", self._c_ls()),
                ("read_range (cut points and bisection, N <= 65536; gzip on the dsk host)", self._c_range("OFF", "N", False)),
                ("read_range (pod_gzip: gzip -1 in the pod)", self._c_range("OFF", "N", True)),
                ("read_filtered (OFF and END are line starts; the pod filters, the dsk host gzips)", self._c_filtered("OFF", "END", alt, False)),
                ("read_filtered (pod_gzip: the pod filters and gzips -1)", self._c_filtered("OFF", "END", alt, True)),
                ("read_heads (every line's time, request and user, any user: the solo check)", self._c_heads("OFF", "END")),
                ("pod_time (the pod's clock, which stamps the log)", self._c_date()),
                ("timed_read (counts bytes, never shows them)", self._c_timed("OFF", "N"))]
        return [x for what, c in cmds for x in (f"# {what}", env + shlex.quote(c))]

    # ---- running them
    def run_raw(self, cmd: str) -> tuple[int, bytes, bytes]:
        """One command through dsk.sh: (returncode, stdout bytes, stderr bytes). Raises only on a dry run or a timeout, never on a nonzero exit."""
        if self.dry_run:
            raise RuntimeError("dry run: no remote command is run")
        run = self._run or (lambda *a, **k: subprocess.run(*a, **k))
        p = run(self._argv(cmd), capture_output=True, timeout=self.timeout_s, env=self._env())
        return p.returncode, p.stdout or b"", p.stderr or b""

    def _call(self, cmd: str, what: str) -> bytes:
        rc, out, err = self.run_raw(cmd)
        if rc != 0:
            raise RuntimeError(f"{what}: dsk.sh exit {rc}: {err[-300:].decode('utf-8', 'replace')}")
        return out

    @staticmethod
    def _gunzip(out: bytes, what: str) -> bytes:
        try:
            return gzip.decompress(out)
        except (EOFError, OSError, zlib.error) as e:        # a truncated stream must never read as an empty one
            raise RuntimeError(f"{what}: the compressed reply is truncated or corrupt: {e}") from e

    @staticmethod
    def _lines_rc(out: bytes, what: str) -> list[str]:
        lines = out.decode("utf-8", "replace").splitlines()
        m = _RC.match(lines[-1]) if lines else None
        if m is None:
            raise RuntimeError(f"{what}: no exit status came back from the remote command (a dead transport?)")
        if m.group(1) != "0":
            raise RuntimeError(f"{what}: remote exit {m.group(1)}")
        return lines[:-1]

    def tools(self) -> dict[str, bool]:
        got = {}
        for what, cmd, rename in (("tools (pod)", self._c_tools(), {"gzip": "gzip_pod"}), ("tools (dsk host)", self._c_tools_dsk(), {})):
            for ln in self._lines_rc(self._call(cmd, what), what):
                m = re.fullmatch(r"TOOL_(\w+)=([01])", ln)
                if m:
                    got[rename.get(m.group(1), m.group(1))] = m.group(2) == "1"
        return {k: got.get(k, False) for k in TOOLS}

    def stat(self) -> FileStat:
        lines = self._lines_rc(self._call(self._c_stat(), "stat"), "stat")
        m = re.fullmatch(r"(\d+) (\d+)", lines[0]) if len(lines) == 1 else None
        if m is None:
            raise RuntimeError(f"stat: unexpected reply {lines[:3]}")
        return FileStat(int(m.group(1)), int(m.group(2)))

    def siblings(self) -> list[str]:
        names = self._lines_rc(self._call(self._c_ls(), "ls"), "ls")
        if self.name not in names:
            raise RuntimeError(f"ls: {self.path} is not there: is the log on, and did it move? Seen: {names[:10]}")
        return sorted(n for n in names if n != self.name and n.startswith(self.name))

    def read_range(self, off: int, n: int) -> bytes:
        check_off(off), check_n(n)
        body = self._gunzip(self._call(self._c_range(off, n), "read_range"), "read_range")
        m = re.search(rb"\nICSA_DD_RC=(\d+)\n\Z", body)
        if m is None:
            raise RuntimeError("read_range: no dd status came back (a dead transport?)")
        if m.group(1) != b"0":
            raise RuntimeError(f"read_range: dd exit {m.group(1).decode()}: does the pod's dd take iflag=skip_bytes,count_bytes?")
        data = body[:m.start()]
        if len(data) > n:
            raise RuntimeError(f"read_range: {len(data)} bytes came back for {n}")
        return data

    def read_filtered(self, off: int, end: int, users: Sequence[str]) -> bytes:
        off, end = check_span(off, end)
        alt = _pattern(users)                  # validates every id before any command is built
        if end == off:
            return b""
        body = self._gunzip(self._call(self._c_filtered(off, end, alt), "read_filtered"), "read_filtered")
        m = re.search(rb"(?:^|\n)ICSA_DD_RC=(\d+)\nICSA_PULL_RC=(\d+)\n\Z", body)
        if m is None:
            raise RuntimeError("read_filtered: no exit status came back from the remote read (a dead transport?)")
        if m.group(1) != b"0":
            raise RuntimeError(f"read_filtered: dd exit {m.group(1).decode()}: does the pod's dd take iflag=skip_bytes,count_bytes?")
        if m.group(2) not in (b"0", b"1"):         # grep: 1 = no line matched
            raise RuntimeError(f"read_filtered: grep exit {m.group(2).decode()}")
        return body[:m.start() + 1] if body[m.start():m.start() + 1] == b"\n" else body[:m.start()]

    def read_heads(self, off: int, end: int) -> bytes:
        """Every line's head in [off, end) (its time, request and user, `[ts] request: X; user: U;`), whoever the user: the solo check must see users
        no slot map names. The same in-band dd status and truncation checks as read_filtered."""
        off, end = check_span(off, end)
        if end == off:
            return b""
        body = self._gunzip(self._call(self._c_heads(off, end), "read_heads"), "read_heads")
        m = re.search(rb"(?:^|\n)ICSA_DD_RC=(\d+)\nICSA_PULL_RC=(\d+)\n\Z", body)
        if m is None:
            raise RuntimeError("read_heads: no exit status came back from the remote read (a dead transport?)")
        if m.group(1) != b"0":
            raise RuntimeError(f"read_heads: dd exit {m.group(1).decode()}")
        if m.group(2) not in (b"0", b"1"):
            raise RuntimeError(f"read_heads: grep exit {m.group(2).decode()}")
        return body[:m.start() + 1] if body[m.start():m.start() + 1] == b"\n" else body[:m.start()]

    def pod_time(self) -> float:
        """The pod's clock now (epoch s): the clock site_g's log stamps lines with."""
        lines = self._lines_rc(self._call(self._c_date(), "pod_time"), "pod_time")
        try:
            return float(lines[-1])
        except (IndexError, ValueError) as e:
            raise RuntimeError(f"pod_time: no time came back: {lines[-2:]}") from e

    def timed_read(self, off: int, n: int) -> tuple[float, int]:
        check_off(off), check_n_big(n)
        lines = self._lines_rc(self._call(self._c_timed(off, n), "timed_read"), "timed_read")
        m = re.fullmatch(r"ICSA_TIMED (\S+) (\S+) (\d+)", lines[-1]) if lines else None
        if m is None:
            raise RuntimeError(f"timed_read: unexpected reply {lines[-2:]}")
        try:
            secs = float(m.group(2)) - float(m.group(1))
        except ValueError as e:                      # a date without %N prints the letters back: no timing, not a made-up one
            raise RuntimeError(f"timed_read: the pod's date gave no sub-second time: {m.group(1)!r}") from e
        return secs, int(m.group(3))
