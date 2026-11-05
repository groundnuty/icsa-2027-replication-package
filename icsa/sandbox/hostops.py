"""Host-side helpers: docker, sudo, loop-mounted quota disks, TLS material."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path


class SandboxError(RuntimeError):
    pass


def run(cmd: list[str], *, input: str | None = None, timeout: float | None = 120,
        env: dict | None = None, check: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, input=input, capture_output=True, text=True, timeout=timeout, env=env)
    if check and p.returncode != 0:
        # never include env (secrets) in the message
        raise SandboxError(f"{' '.join(cmd[:4])}... failed ({p.returncode}): {p.stderr.strip()[:500]}")
    return p


def run_bounded(cmd: list[str], timeout_s: float) -> subprocess.CompletedProcess:
    """Run `cmd` and wait at most `timeout_s`, never raising: rc 124 on the deadline, 127 when it cannot be started.

    Unlike `subprocess.run(timeout=)`, which kills the child and then waits for its pipes without a limit, a command
    stuck in the kernel (a umount in D state, a grandchild of sudo holding the pipes) cannot hold the caller: on the
    deadline it gets SIGTERM (sudo relays it), then SIGKILL, and is abandoned. Output goes to files, not pipes."""
    import signal
    import tempfile
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        try:
            p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
        except OSError as e:
            return subprocess.CompletedProcess(cmd, 127, "", repr(e)[:300])
        deadline = time.monotonic() + timeout_s
        while p.poll() is None and time.monotonic() < deadline:
            time.sleep(0.05)
        timed_out = p.returncode is None
        if timed_out:
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(p.pid, sig)
                except OSError:
                    try:
                        p.send_signal(sig)
                    except OSError:
                        pass
                grace = time.monotonic() + 1.0
                while p.poll() is None and time.monotonic() < grace:
                    time.sleep(0.05)
                if p.returncode is not None:
                    break
        out.seek(0)
        err.seek(0)
        so, se = out.read().decode(errors="replace"), err.read().decode(errors="replace")
    if timed_out:
        return subprocess.CompletedProcess(cmd, 124, so, (se + "\n" if se else "") + f"timed out after {timeout_s} s")
    return subprocess.CompletedProcess(cmd, p.returncode, so, se)


def sudo_bounded(*args: str, timeout_s: float) -> subprocess.CompletedProcess:
    return run_bounded(list(args) if os.geteuid() == 0 else ["sudo", "-n", *args], timeout_s)


_STUCK_READS: dict = {}


def read_text_bounded(path: Path | str, timeout_s: float) -> str | None:
    """The text of `path`, or None when it cannot be read or the read does not finish within `timeout_s` (reading
    /proc/*/mountinfo waits on the mount-namespace lock, the lock a stuck unmount holds). A read of the same path still
    stuck from an earlier call is not repeated: None at once, so stuck reads cannot pile up."""
    import threading
    key = str(path)
    t = _STUCK_READS.get(key)
    if t is not None:
        if t.is_alive():
            return None
        _STUCK_READS.pop(key, None)
    box: dict = {}

    def rd():
        try:
            box["text"] = Path(path).read_text()
        except (OSError, UnicodeDecodeError) as e:
            box["error"] = e
    t = threading.Thread(target=rd, daemon=True, name=f"read:{key}")
    t.start()
    t.join(timeout_s)
    if t.is_alive():
        _STUCK_READS[key] = t
        return None
    return box.get("text")
_HOST_FACTS: dict | None = None


def host_facts() -> dict:
    """What this host runs that decides how a run's memory and disk behave, for every run record (science, #2, 2 Nov 02:34Z; the D kill on
    kernel 7.0 is why): the kernel, Docker's version, its storage driver and cgroup setup. A value that cannot be read is None, never a guess,
    and is asked again next time; a complete answer is kept for the process."""
    global _HOST_FACTS
    if _HOST_FACTS is not None:
        return dict(_HOST_FACTS)
    import platform
    out: dict = {"kernel": platform.release(), "docker_version": None, "storage_driver": None, "cgroup_driver": None, "cgroup_version": None}
    try:
        r = run(["docker", "info", "-f", "{{.ServerVersion}}|{{.Driver}}|{{.CgroupDriver}}|{{.CgroupVersion}}"], check=False, timeout=30)
        parts = r.stdout.strip().split("|")
        if r.returncode == 0 and len(parts) == 4 and all(parts):
            out.update(zip(("docker_version", "storage_driver", "cgroup_driver", "cgroup_version"), parts))
            _HOST_FACTS = dict(out)
    except Exception:  # noqa: BLE001 -- a record must still be written
        pass
    return out


def docker(*args: str, **kw) -> subprocess.CompletedProcess:
    return run(["docker", *args], **kw)


def _docker_t(*args: str, timeout: float = 30) -> subprocess.CompletedProcess:
    """docker with a bounded wait that reports a timeout as a failed result (rc 124) instead of raising."""
    try:
        return docker(*args, check=False, timeout=timeout)
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(["docker", *args], 124, "", "timed out")


def _state(kind: str, name: str) -> str:
    """"present", "absent" (the daemon said the object does not exist) or "unknown" (anything else: daemon down,
    timeout). Only an explicit answer counts as absence."""
    r = _docker_t(kind, "inspect", name)
    if r.returncode == 0:
        return "present"
    err = r.stderr.lower()
    # only the daemon's own answer about this object ("Error response from daemon: No such container: x" /
    # "network x not found"); a missing socket ("dial unix ...: no such file or directory") or "Cannot connect" is not one
    if "error response from daemon" in err and (f"no such {kind}" in err or f"{kind} {name.lower()} not found" in err
                                                or f"no such {kind}: {name.lower()}" in err):
        return "absent"
    return "unknown"


def network_state(name: str) -> str:
    return _state("network", name)


def container_state(name: str) -> str:
    return _state("container", name)


def remove_container(name: str, tries: int = 4) -> None:
    """`docker rm -f` and VERIFY the container is gone (absence only on an explicit daemon answer)."""
    for i in range(tries):
        if container_state(name) == "absent":
            return
        _docker_t("rm", "-f", name)
        if container_state(name) == "absent":
            return
        time.sleep(0.5 * (i + 1))
    st = container_state(name)
    if st != "absent":
        raise SandboxError(f"docker container {name} could not be removed (state: {st})")


def remove_network(name: str, tries: int = 5) -> None:
    """Remove a sandbox network and VERIFY it is gone, force-disconnecting stuck endpoints between tries.

    A leaked network keeps its subnet; that is what exhausted Docker's default pools. Raises SandboxError unless the
    daemon explicitly reports the network absent at the end (daemon trouble is not absence). The caller finishes its
    other cleanup first."""
    for i in range(tries):
        st = network_state(name)
        if st == "absent":
            return
        if st == "present":
            r = _docker_t("network", "rm", name)
            if r.returncode == 0 and network_state(name) == "absent":
                return
            eps = _docker_t("network", "inspect", "-f", "{{range .Containers}}{{.Name}} {{end}}", name).stdout.split()
            for c in eps:
                _docker_t("network", "disconnect", "-f", name, c)
        time.sleep(0.5 * (i + 1))
    st = network_state(name)
    if st != "absent":
        raise SandboxError(f"docker network {name} could not be removed (state: {st})")


def image_id(ref: str) -> str:
    """The immutable id (sha256:...) a tag or id currently resolves to."""
    return docker("image", "inspect", "-f", "{{.Id}}", ref).stdout.strip()


def sudo(*args: str, **kw) -> subprocess.CompletedProcess:
    if os.geteuid() == 0:
        return run(list(args), **kw)
    return run(["sudo", "-n", *args], **kw)


def have_sudo() -> bool:
    return os.geteuid() == 0 or run(["sudo", "-n", "true"], check=False).returncode == 0


def make_quota_dir(img: Path, mnt: Path, size_bytes: int, uid: int, usable: bool = False) -> None:
    """A fresh ext4 filesystem of exactly this size, loop-mounted at mnt, owned by uid.

    The size is a hard limit: writes beyond it fail with ENOSPC. Needs sudo for
    the mount only; the image is a sparse file, so a 48 GB disk costs nothing
    until it is written.
    """
    if usable:  # the quota is what the agent can write: add the filesystem's own overhead
        from icsa.sandbox.config import usable_image_bytes
        size_bytes = usable_image_bytes(size_bytes)
    img.parent.mkdir(parents=True, exist_ok=True)
    mnt.mkdir(parents=True, exist_ok=True)
    with open(img, "wb") as f:
        f.truncate(size_bytes)
    run(["mkfs.ext4", "-q", "-F", "-m", "0", "-i", "65536", "-O", "^has_journal", "-E", "lazy_itable_init=1,nodiscard", str(img)],
        timeout=300)
    sudo("mount", "-o", "loop,nosuid,nodev", str(img), str(mnt))
    sudo("rmdir", str(mnt / "lost+found"), check=False)
    sudo("chown", f"{uid}:{uid}", str(mnt))


def _unescape_mountinfo(field: str) -> str:
    """mountinfo writes space, tab, newline and backslash in a path as octal escapes (\\040, ...)."""
    import re
    return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), field)


def unmount(mnt: Path) -> None:
    """Lazy-unmount everything stacked at mnt. The oneclient FUSE mount sits on top of the bind mount at the same
    path, so one umount removes only the top of the stack and leaves the bind behind: repeat while it is a mount point."""
    mnt = Path(mnt)
    path = os.path.join(os.path.realpath(mnt.parent), mnt.name)     # only the parent is resolved: resolving the path itself would stat what is mounted there
    for _ in range(8):
        sudo_bounded("umount", "-l", path, timeout_s=20.0)
        text = read_text_bounded("/proc/self/mountinfo", 5.0)
        if text is None:                 # the mount table cannot be read in time: not known to be gone, and `stop()` must not wait on it for ever
            raise SandboxError(f"unmount of {path}: the mount table could not be read in time")
        if not any(len(f := line.split()) > 4 and _unescape_mountinfo(f[4]) == path for line in text.splitlines()):
            return
    raise SandboxError(f"{path} is still mounted after 8 lazy unmounts")


def make_ca(tls_dir: Path, hosts: list[str]) -> None:
    """A per-run CA and one leaf certificate (+key) per host name, via the openssl CLI."""
    tls_dir.mkdir(parents=True, exist_ok=True)
    ca_key, ca_pem = tls_dir / "ca.key", tls_dir / "ca.pem"
    run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(ca_key), "-out", str(ca_pem),
         "-days", "2", "-subj", "/CN=icsa-sandbox-run-ca"])
    for h in hosts:
        key, csr, pem = tls_dir / f"{h}.key", tls_dir / f"{h}.csr", tls_dir / f"{h}.pem"
        run(["openssl", "req", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key), "-out", str(csr),
             "-subj", f"/CN={h}"])
        ext = tls_dir / f"{h}.ext"
        ext.write_text(f"subjectAltName=DNS:{h}\n")
        run(["openssl", "x509", "-req", "-in", str(csr), "-CA", str(ca_pem), "-CAkey", str(ca_key),
             "-CAcreateserial", "-out", str(pem), "-days", "2", "-extfile", str(ext)])
        csr.unlink()
        ext.unlink()
        key.chmod(0o644)  # read by the gate container's root only; the dir is not mounted anywhere else
    ca_key.unlink()       # the CA key is not needed after signing: nothing can mint more certificates


def jdump(obj) -> str:
    return json.dumps(obj, indent=1, default=str)


def fuse_mounts(mountinfo: str) -> list[dict]:
    """Every FUSE mount of a mountinfo text: {"mount_id", "dev" ("0:N"; N names /sys/fs/fuse/connections/N), "mountpoint"
    (unescaped), "fstype"}. Not fusectl, the control filesystem at /sys/fs/fuse/connections."""
    out = []
    for line in mountinfo.splitlines():
        pre, sep, post = line.partition(" - ")
        f, g = pre.split(), post.split()
        if sep and len(f) >= 5 and g and (g[0] in ("fuse", "fuseblk") or g[0].startswith(("fuse.", "fuseblk."))):
            out.append({"mount_id": f[0], "dev": f[2], "mountpoint": _unescape_mountinfo(f[4]), "fstype": g[0]})
    return out


def is_fuse_mounted(mountinfo: str, mountpoint: str) -> bool:
    """True if mountinfo (the text of /proc/self/mountinfo) has a FUSE filesystem at mountpoint.

    Fields: id parent major:minor root mountpoint options [optional...] - fstype source superopts
    """
    for line in mountinfo.splitlines():
        pre, sep, post = line.partition(" - ")
        f = pre.split()
        if sep and len(f) >= 5 and f[4] == mountpoint and post.split()[0].startswith("fuse"):
            return True
    return False
