"""What keeps the command inside its `--out`: the path checks before it starts, a write guard (an audit hook) while it runs, and the capture of
everything the libraries print."""
from __future__ import annotations

import contextlib
import os
import subprocess
import sys
from pathlib import Path


class GuardError(RuntimeError):
    pass


def check_out(out: Path, campaign_root: Path, resume_cut: bool = False) -> Path:
    """`out` must be a new (or empty) directory that is neither inside the campaign's root or a run directory, nor holds it, and, if it is inside a git work
    tree, an ignored path (science's workspace is a repository: an ignored, untracked path is right; a tracked tree is not).
    `resume_cut` (the `analyse` stage): `out` may hold a cut made by the `cut` stage, and nothing of an analysis (no tables, no pipeline directory)."""
    out = Path(os.path.abspath(out))
    root = Path(os.path.realpath(campaign_root))
    real = Path(os.path.realpath(out))
    if real == root or root in real.parents or real in root.parents:
        raise GuardError("--out and the campaign root are nested: the command never writes into the campaign")
    cut_only = out.is_dir() and (out / "work" / "cut" / "cut.json").is_file() and not (out / "tables").exists() and not (out / "pipeline").exists()
    if out.exists() and (not out.is_dir() or any(out.iterdir())) and not (resume_cut and cut_only):
        raise GuardError("--out exists and is not an empty directory: a snapshot is never written over another")
    probe = out
    while not probe.exists():
        probe = probe.parent
    top = subprocess.run(["git", "-C", str(probe), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode == 0:
        ig = subprocess.run(["git", "-C", top.stdout.strip(), "check-ignore", "-q", "--no-index", str(out)], capture_output=True, text=True)
        if ig.returncode != 0:
            raise GuardError(f"--out is inside the git work tree {top.stdout.strip()} and is not ignored there: use an ignored, untracked path")
    return out


_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
_ALWAYS_OK = ("/dev/null", "/dev/tty", "/dev/stdout", "/dev/stderr")
_PATH_EVENTS = {"os.mkdir": (0,), "os.remove": (0,), "os.rmdir": (0,), "os.truncate": (0,), "os.chmod": (0,), "os.chown": (0,), "os.utime": (0,),
                "os.rename": (0, 1), "os.symlink": (1,), "os.link": (0, 1), "shutil.copyfile": (1,), "shutil.copymode": (1,),
                "shutil.copystat": (1,), "shutil.rmtree": (0,), "shutil.move": (0, 1), "os.mkfifo": (0,), "os.mknod": (0,), "os.setxattr": (0,)}


def _norm(p) -> str | None:
    if isinstance(p, int):
        return None
    try:
        p = os.fspath(p)
        if isinstance(p, bytes):
            p = os.fsdecode(p)
        return os.path.realpath(p)
    except (TypeError, ValueError):
        return None


class WriteGuard:
    """Raises on a Python-level write, create, rename or delete outside `allowed`. It cannot see a C library's own writes (SQLite's -shm beside the
    store, say): the tests compare the campaign's directory before and after for that."""

    def __init__(self, allowed: list[Path]):
        self.allowed = [os.path.realpath(a) for a in allowed]
        self.denied: list[str] = []
        self.active = False

    def _inside(self, p: str) -> bool:
        return p in _ALWAYS_OK or p.startswith("/proc/self/") or any(p == a or p.startswith(a + os.sep) for a in self.allowed)

    def __call__(self, event: str, args: tuple) -> None:
        if not self.active:
            return
        paths: list[str | None] = []
        if event == "open":
            path, mode, flags = args[0], args[1], args[2]
            writes = bool(isinstance(flags, int) and flags & _WRITE_FLAGS) or (isinstance(mode, str) and any(c in mode for c in "wax+"))
            if not writes:
                return
            paths = [_norm(path)]
        elif event in _PATH_EVENTS:
            paths = [_norm(args[i]) for i in _PATH_EVENTS[event] if i < len(args)]
        else:
            return
        for p in paths:
            if p is not None and not self._inside(p):
                self.denied.append(f"{event} {p}")
                raise GuardError(f"write outside --out refused: {event} {p}")

    def install(self) -> "WriteGuard":
        sys.addaudithook(self)
        self.active = True
        return self

    def off(self) -> None:
        self.active = False


@contextlib.contextmanager
def captured(path: Path):
    """Everything written to file descriptors 1 and 2 (this process, its forked workers and its children) goes to `path` for the duration."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sys.stdout.flush()
    sys.stderr.flush()
    saved = os.dup(1), os.dup(2)
    fh = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.dup2(fh, 1)
        os.dup2(fh, 2)
        yield
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(saved[0], 1)
        os.dup2(saved[1], 2)
        for fd in (*saved, fh):
            os.close(fd)
