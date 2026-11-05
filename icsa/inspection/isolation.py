"""Where a Codex coder runs: a container that can read only its own call's files and reach only its model API.

Science, #76, 2 Nov 04:50Z and 04:57Z: Codex's read-only mode restricts writes, not reads, so a coder on the host could read
K's truth, the repo or another packet. Each call therefore gets, and loses when it ends:
  * a coder container on NO network (`--network none`: loopback only). An `--internal` docker network is not enough: its
    gateway is the host, and every host service listening on all interfaces answered from it (Codex review, measured 2 Nov);
  * an allowlisting CONNECT proxy (`coderproxy.py`) in its own container, which reaches only the listed hosts, port 443, and
    logs every request it allows or refuses. The coder reaches it only through a Unix socket in a directory holding nothing
    else, via a forwarder (`coderfwd.py`) from localhost inside the coder's container;
  * the coder container holds only the static codex binary (read-only), a CODEX_HOME directory with a COPY of the login
    (never the original), an io directory with the answer schema, the forwarder and the socket. The packet arrives on stdin.
    No other host path is mounted. Root is read-only, capabilities are dropped, memory and pids are capped.
Any failure to set this up raises `IsolationError`. There is no launch without it.

The launcher takes an argv whose paths are written as {HOME}, {IO} and {CWD}, and maps them to the container's paths.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

# python:3.12-slim, the campaign image's own base (sandbox/Dockerfile FROM): nothing of this project is in it.
BASE_IMAGE = "python@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf"
PROXY_SCRIPT = Path(__file__).with_name("coderproxy.py")
FWD_SCRIPT = Path(__file__).with_name("coderfwd.py")
# Hosts the coder may reach. Set from a deny-and-log discovery run (lane-k, 2 Nov), not guessed: see ALLOW_NOTE.
ALLOW_HOSTS: tuple[str, ...] = ("host-15.invalid",)
ALLOW_NOTE = ("lane-k, 2 Nov 14:43Z, codex 0.166.0 with a ChatGPT login behind a deny-all proxy: host-15.invalid:443 is the only host it "
              "asked for (with coders.CODEX_DISABLE applied, no backend-api/ps/mcp request remains)")
LABEL = "icsa.inspection.coder=1"
IN_HOME, IN_IO, IN_CWD = "/codex-home", "/io", "/work"
PROXY_PORT = 3128
CODER_MEMORY, PROXY_MEMORY = "2g", "256m"
# This host hangs instead of OOM-killing (lead, 2 Nov 14:4xZ): no coder starts with less memory available than this. With
# several coders in parallel a start WAITS for memory (up to MEM_WAIT_S) rather than failing a coder's attempt.
MIN_AVAILABLE_GIB = 16.0
MEM_WAIT_S, MEM_POLL_S = 600, 5
MAX_PARALLEL = 12           # lead, 2 Nov 17:38Z: under ~12 coder containers at 2 GiB each on this host
# Calls in flight in THIS process: their containers are not leftovers (parallel coders, science #2 17:38Z).
_ACTIVE: set[str] = set()
_ACTIVE_LOCK = threading.Lock()
_LOGIN_LOCK = threading.Lock()   # the login's snapshot (seed_home) and publication (settle_login) never interleave


def mem_available_gib(meminfo: str = "/proc/meminfo") -> float:
    for ln in Path(meminfo).read_text().splitlines():
        if ln.startswith("MemAvailable:"):
            return int(ln.split()[1]) / 2**20
    raise IsolationError("MemAvailable not found in /proc/meminfo")


class IsolationError(RuntimeError):
    """The isolated launch could not be set up (or torn down cleanly): the call must not happen."""


@dataclass
class Launch:
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False
    archive: dict = field(default_factory=dict)   # proxy.jsonl, isolation.json
    proxy: dict = field(default_factory=dict)     # {"allowed": [...], "denied": [...], "errors": [...]}


def _docker(*args: str, check: bool = True, timeout: int = 60, input: str | None = None) -> subprocess.CompletedProcess:
    p = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout, input=input)
    if check and p.returncode != 0:
        raise IsolationError(f"docker {args[0]} failed ({p.returncode}): {p.stderr.strip()[-300:]}")
    return p


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def preflight(image: str = BASE_IMAGE) -> dict:
    """Refuse to start a run unless docker answers, the base image is here and the proxy script exists."""
    if shutil.which("docker") is None:
        raise IsolationError("docker is not installed")
    _docker("version", "--format", "{{.Server.Version}}")
    _docker("image", "inspect", image, "--format", "{{.Id}}")
    for f in (PROXY_SCRIPT, FWD_SCRIPT):
        if not f.is_file():
            raise IsolationError(f"isolation script missing: {f}")
    return {"image": image, "proxy_sha256": sha256_file(PROXY_SCRIPT)}


def read_proxy_log(text: str) -> dict:
    allowed, denied, errors, ready = [], [], [], False
    for ln in text.splitlines():
        try:
            ev = json.loads(ln)
        except json.JSONDecodeError:
            errors.append("unparsable proxy log line")
            continue
        e = ev.get("event")
        if e == "ready":
            ready = True
        elif e == "allow":
            allowed.append(ev.get("target"))
        elif e == "deny":
            denied.append(ev.get("target"))
        elif e == "error":
            errors.append(ev.get("target"))
    return {"ready": ready, "allowed": sorted(set(allowed)), "denied": sorted(set(x for x in denied if x)),
            "errors": [x for x in errors if x]}


class DockerLauncher:
    """Runs one codex call inside the isolation above. `allow` None means ALLOW_HOSTS; () means deny everything (discovery)."""

    # codex runs commands through these helpers, installed beside it. A coder never gets them, so even a tool call it
    # attempts cannot run (seen 2 Nov: "failed to spawn code-mode host"); the canary mounts them for its positive control.
    HELPERS = ("codex-code-mode-host", "codex-exec-server")

    def __init__(self, codex_bin: str | None = None, *, image: str = BASE_IMAGE, allow: tuple[str, ...] | None = None,
                 auth_src: str | None = None, helpers: bool = False):
        found = codex_bin or shutil.which("codex")
        if not found:
            raise IsolationError("codex binary not found")
        self.codex_bin = str(Path(found).resolve())
        self.helpers = [str(Path(self.codex_bin).with_name(h)) for h in self.HELPERS] if helpers else []
        for h in self.helpers:
            if not Path(h).is_file():
                raise IsolationError(f"codex helper missing: {h}")
        self.image = image
        self.allow = tuple(ALLOW_HOSTS if allow is None else allow)
        self.auth_src = Path(auth_src) if auth_src else Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "auth.json"

    def preflight(self) -> dict:
        return {**preflight(self.image), "codex_sha256": sha256_file(Path(self.codex_bin)), "allow": list(self.allow)}

    # ---- the login copy -------------------------------------------------------------------------------------------
    def seed_home(self, home: Path) -> str | None:
        """Copy (never link) the login into the call's CODEX_HOME. Returns the sha256 of the COPY, taken under the login
        lock: with parallel coders, hashing the source could catch another call's refresh published after this copy was
        made, and settle_login would then carry this stale copy back over it (final pinned pass S5, 2 Nov)."""
        with _LOGIN_LOCK:
            if not self.auth_src.is_file():
                return None
            dst = home / "auth.json"
            shutil.copyfile(self.auth_src, dst)
            dst.chmod(0o600)
            return sha256_file(dst)

    def settle_login(self, home: Path, sha_at_copy: str | None) -> dict:
        """If codex refreshed the login inside the container, carry the refreshed copy back, so a rotated refresh token
        cannot leave the host's own login stale. Only when the original is unchanged since the copy, and the new file
        is JSON with the same top-level keys."""
        with _LOGIN_LOCK:      # one snapshot or publication at a time across parallel coders
            return self._settle_login(home, sha_at_copy)

    def _settle_login(self, home: Path, sha_at_copy: str | None) -> dict:
        copy = home / "auth.json"
        if sha_at_copy is None or not copy.is_file():
            return {"auth": "none"}
        if sha256_file(copy) == sha_at_copy:
            return {"auth": "unchanged"}
        try:
            new, old = json.loads(copy.read_text()), json.loads(self.auth_src.read_text())
        except (OSError, json.JSONDecodeError):
            return {"auth": "changed, not carried back: unreadable"}
        if sha256_file(self.auth_src) != sha_at_copy:
            return {"auth": "changed, not carried back: the original changed meanwhile"}
        if not isinstance(new, dict) or set(new) != set(old):
            return {"auth": "changed, not carried back: different shape"}
        tmp = self.auth_src.with_name(f".auth.json.{secrets.token_hex(4)}")
        tmp.write_text(copy.read_text())
        tmp.chmod(0o600)
        os.replace(tmp, self.auth_src)
        return {"auth": "refreshed, carried back"}

    # ---- one call -------------------------------------------------------------------------------------------------
    def run(self, argv: list[str], message: str, home: Path, io: Path, timeout_s: int, *,
            entrypoint: str | None = None) -> Launch:
        """`argv` follows the entrypoint (codex by default); {HOME}/{IO}/{CWD} in it become the container's paths.
        `entrypoint` other than codex is for the isolation canary only."""
        home, io = Path(home), Path(io)
        t0 = time.monotonic()
        while (avail := mem_available_gib()) < MIN_AVAILABLE_GIB:
            if time.monotonic() - t0 > MEM_WAIT_S:
                raise IsolationError(f"only {avail:.1f} GiB available, below {MIN_AVAILABLE_GIB:.0f}, for {MEM_WAIT_S} s: no coder starts")
            time.sleep(MEM_POLL_S)
        name = f"icsa-coder-{secrets.token_hex(5)}"
        with _ACTIVE_LOCK:
            left = leftovers()
            if left:      # a teardown that failed earlier stops every later launch, never silently piles up
                raise IsolationError(f"{len(left)} coder containers or networks left from an earlier call: remove them first")
            _ACTIVE.add(name)
        try:
            return self._run(name, argv, message, home, io, timeout_s, entrypoint, avail)
        finally:
            with _ACTIVE_LOCK:
                _ACTIVE.discard(name)

    def _run(self, name, argv, message, home, io, timeout_s, entrypoint, avail) -> Launch:
        proxy, coder = f"{name}-proxy", f"{name}-coder"
        logdir = Path(tempfile.mkdtemp(prefix="coder-proxy-"))   # outside every mount the coder has
        sockdir = Path(tempfile.mkdtemp(prefix="coder-sock-"))   # holds only the proxy's socket
        sockdir.chmod(0o755)
        uid = f"{os.getuid()}:{os.getgid()}"
        meta = {"mem_available_gib": round(avail, 1), "helpers": [Path(h).name for h in self.helpers], "coder_network": "none",
                "image": self.image, "allow": list(self.allow), "codex_sha256": sha256_file(Path(self.codex_bin)),
                "proxy_sha256": sha256_file(PROXY_SCRIPT), "fwd_sha256": sha256_file(FWD_SCRIPT)}
        created, problems, plog = [], [], ""
        try:
            _docker("run", "-d", "--name", proxy, "--label", LABEL, "--network", "bridge",
                    "--memory", PROXY_MEMORY, "--memory-swap", PROXY_MEMORY, "--pids-limit", "128",
                    "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--read-only", "--user", uid,
                    "-e", "PYTHONDONTWRITEBYTECODE=1",
                    "-v", f"{PROXY_SCRIPT}:/proxy.py:ro", "-v", f"{logdir}:/log:rw", "-v", f"{sockdir}:/sock:rw",
                    "--entrypoint", "python3", self.image,
                    "-I", "/proxy.py", "--listen", "unix:/sock/proxy.sock", "--allow", ",".join(self.allow),
                    "--log", "/log/proxy.jsonl")
            created.append(proxy)
            log = logdir / "proxy.jsonl"
            t0 = time.monotonic()
            while not (log.is_file() and read_proxy_log(log.read_text())["ready"] and (sockdir / "proxy.sock").exists()):
                if time.monotonic() - t0 > 20:
                    raise IsolationError("the proxy did not become ready in 20 s")
                time.sleep(0.2)
            purl = f"http://localhost:{PROXY_PORT}"
            mapped = [a.replace("{HOME}", IN_HOME).replace("{IO}", IN_IO).replace("{CWD}", IN_CWD) for a in argv]
            # no network at all (no gateway to the host): the forwarder turns loopback into the proxy's socket
            wrapper = (f"python3 -I /fwd.py {PROXY_PORT} /sock/proxy.sock /tmp/fwd.ready & i=0; "
                       "while [ ! -e /tmp/fwd.ready ] && [ $i -lt 100 ]; do sleep 0.1; i=$((i+1)); done; "
                       '[ -e /tmp/fwd.ready ] || { echo "forwarder did not start" >&2; exit 97; }; exec "$0" "$@"')
            cmd = ["run", "-i", "--rm", "--name", coder, "--label", LABEL, "--network", "none",
                   "--memory", CODER_MEMORY, "--memory-swap", CODER_MEMORY, "--pids-limit", "512",
                   "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--read-only", "--user", uid,
                   "--tmpfs", "/tmp:rw,size=512m", "--tmpfs", f"{IN_CWD}:rw,size=64m", "-w", IN_CWD,
                   "-e", "HOME=/tmp", "-e", f"CODEX_HOME={IN_HOME}", "-e", "PYTHONDONTWRITEBYTECODE=1",
                   "-e", f"HTTPS_PROXY={purl}", "-e", f"https_proxy={purl}", "-e", f"HTTP_PROXY={purl}",
                   "-e", f"http_proxy={purl}", "-e", f"ALL_PROXY={purl}", "-e", "NO_PROXY=", "-e", "no_proxy=",
                   "-e", "SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt",
                   "-v", f"{self.codex_bin}:/usr/local/bin/codex:ro",
                   *[a for h in self.helpers for a in ("-v", f"{h}:/usr/local/bin/{Path(h).name}:ro")],
                   "-v", f"{FWD_SCRIPT}:/fwd.py:ro", "-v", f"{sockdir}:/sock:rw",
                   "-v", f"{home}:{IN_HOME}:rw", "-v", f"{io}:{IN_IO}:rw",
                   "--entrypoint", "/bin/sh", self.image, "-c", wrapper, entrypoint or "/usr/local/bin/codex", *mapped]
            created.append(coder)
            try:
                p = subprocess.run(["docker", *cmd], input=message, capture_output=True, text=True, timeout=timeout_s)
                out = Launch(p.returncode, p.stdout, p.stderr)
            except subprocess.TimeoutExpired as e:
                so = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
                se = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
                out = Launch(None, so, se, timed_out=True)
        finally:
            for obj in reversed(created):
                p = _docker("rm", "-f", obj, check=False)
                if p.returncode != 0 and "No such" not in p.stderr:
                    problems.append(f"container {obj}: {p.stderr.strip()[-200:]}")
            plog = (logdir / "proxy.jsonl").read_text() if (logdir / "proxy.jsonl").is_file() else ""
            shutil.rmtree(logdir, ignore_errors=True)
            shutil.rmtree(sockdir, ignore_errors=True)
        meta["teardown_problems"] = problems
        out.proxy = read_proxy_log(plog)
        out.archive = {"proxy.jsonl": plog, "isolation.json": json.dumps(meta, indent=1)}
        return out


def leftovers() -> list[str]:
    """Labelled containers and networks that no call in flight in this process owns: what a killed run or a failed
    teardown left behind. A failed query is never read as "none left" (Codex delta review, 2 Nov): it raises."""
    c = _docker("ps", "-a", "--filter", f"label={LABEL}", "--format", "{{.Names}}").stdout.split()
    n = _docker("network", "ls", "-q", "--filter", f"label={LABEL}").stdout.split()
    mine = tuple(_ACTIVE)
    return [x for x in c if not x.startswith(mine or ("\0",))] + n
