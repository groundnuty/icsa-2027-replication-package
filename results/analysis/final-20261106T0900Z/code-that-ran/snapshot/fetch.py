"""Fetch the campaign's store and its finished runs' directories from the run host into one local directory D, with no ssh needed afterwards:

    python -m snapshot.fetch --src-host ubuntu@HOST --ssh "ssh -o BatchMode=yes ..." --campaign-root R --dest D --bwlimit-kib N [--min-free-gib 20]

It is meant to be run again and again into the same D (every 10 minutes, say). Each time:
1. On the source: a consistent copy of R/state.sqlite (`VACUUM INTO` over a READ-ONLY connection; a store with no -wal/-shm is copied as bytes, since a read-only
   open would create them) into a uniquely named temporary file OUTSIDE R's tree, after a free-space check, never over an existing file. Nothing is ever written in R.
2. The copy is transferred (low priority, bandwidth limit) to D/.fetch/state.sqlite.new, checked (sha256 against the source's, integrity_check) and the temporary
   copy on the source is removed (only that file). On any failure the temporary file's path is printed, removed or not. On success nothing about it is printed.
3. From the new copy only the finished runs' directories are read (a done attempt of a done run: `run_dir` paths and counts, never a label, token count or content).
   Each directory is pulled alone (`snapshot.pull`'s command: ionice idle, nice 19, bandwidth limit, no delete, recursive) to the same absolute path below D, with a
   disk-space floor checked before each. When rsync exits 0 for it, `<run_dir>.pulled.json` is written beside it by atomic rename: its file count and bytes, and the
   attempt it stands for. A directory with a valid marker is skipped (no rsync). A marker is valid only if the store copy still lists that same path as the finished
   attempt (same attempt id and end time) AND the directory on disk still has the marker's file count and bytes; otherwise the marker is deleted first and the directory
   pulled again. A killed or failed rsync therefore leaves no marker and is retried next time. Run directories are per attempt (`attempt<N>.try<M>`, M counts the run's
   attempts, so a path is never reused), which is why a finished attempt's directory does not change on the source; the checks above make that a rule, not an assumption.
4. Only when every finished directory has its marker, the new copy's `run_dir` values get D prepended (the pulled directories sit at D/<recorded absolute path>, and
   the pipeline reads the recorded path) and it replaces D/state.sqlite by atomic rename: a reader sees the old copy or the new, never a torn one, and every directory the
   store at D lists as finished is there. Then `cut` and `analyse` take `--campaign-root D` with no further step. Otherwise the old state.sqlite stays and the exit is 1.

D is created mode 700, refused if it exists with broader permissions, is not ours, or holds something that is not a previous fetch's layout (no .fetch/layout.json).
Stdout on success: one line of counts. Nothing per option is read or printed."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shlex
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path

from . import pull

PREFIX = "icsa-snapshot-fetch-"
MARK = ".pulled.json"
PRIORITY = "ionice idle, nice 19"                  # `pull.argv`'s prefix, as the record states it
WORK = ".fetch"
FORMAT = "icsa-snapshot-fetch-v1"


class FetchError(RuntimeError):
    def __init__(self, msg: str, tmp: str | None = None, removed: bool | None = None):
        super().__init__(msg)
        self.tmp, self.removed = tmp, removed       # the source's temporary copy: its path if one may exist, and whether it was removed


# What runs on the source host, from stdin: `python3 - copy ROOT TMP MIN_FREE_BYTES` or `python3 - rm TMP`. Prints one JSON line, or a reason on stderr and exit 1.
REMOTE = r'''
import hashlib, json, os, shutil, sqlite3, sys
from pathlib import Path
os.umask(0o077)
PREFIX = %(prefix)r
def die(m):
    print(m, file=sys.stderr); sys.exit(1)
mode = sys.argv[1]
tmp = Path(sys.argv[3] if mode == "copy" else sys.argv[2])
if not (tmp.is_absolute() and tmp.name.startswith(PREFIX) and tmp.suffix == ".sqlite"):
    die("not a fetch temporary path: %%s" %% tmp)
if mode == "rm":
    try:
        tmp.unlink()
        print(json.dumps({"removed": True}))
    except FileNotFoundError:
        print(json.dumps({"removed": False}))
    sys.exit(0)
root, min_free = Path(sys.argv[2]), int(sys.argv[4])
src = root / "state.sqlite"
if not (root.is_absolute() and src.is_file()):
    die("no campaign store at %%s" %% src)
tdir = tmp.parent
if not tdir.is_dir():
    die("no directory %%s for the temporary copy" %% tdir)
rr, rt = Path(os.path.realpath(root)), Path(os.path.realpath(tdir))
if rt == rr or rr in rt.parents:
    die("the temporary copy would be inside the campaign root")
if os.path.lexists(tmp):
    die("%%s exists: never overwritten" %% tmp)
side = [src.with_name(src.name + s) for s in ("-wal", "-shm")]
size = src.stat().st_size + sum(p.stat().st_size for p in side if p.exists())
free = shutil.disk_usage(tdir).free
if free < 2 * size + min_free:
    die("%%d bytes free in %%s, under 2 x the store (%%d) + the floor (%%d)" %% (free, tdir, size, min_free))
live = None
try:
    if not any(p.exists() for p in side):
        with open(src, "rb") as a, open(tmp, "xb") as b:
            shutil.copyfileobj(a, b, 1 << 20)
        if any(p.exists() for p in side):
            tmp.unlink()
        else:
            live = False
    if live is None:
        con = sqlite3.connect(src.as_uri() + "?mode=ro", uri=True, timeout=30)
        try:
            con.execute("VACUUM INTO '" + str(tmp).replace("'", "''") + "'")
        finally:
            con.close()
        live = True
    h = hashlib.sha256()
    with open(tmp, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
except BaseException:
    try:
        tmp.unlink()
    except FileNotFoundError:
        pass
    raise
print(json.dumps({"bytes": tmp.stat().st_size, "sha256": h.hexdigest(), "live": live}))
''' % {"prefix": PREFIX}


def _utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def prepare_dest(dest: Path) -> Path:
    """D: created 700, or an existing one that is ours, 700-or-narrower, and either empty or a previous fetch's. Returns its real path."""
    d = Path(os.path.abspath(dest))
    if d.exists():
        if not d.is_dir():
            raise SystemExit(f"--dest {d} is not a directory")
        st = d.stat()
        if st.st_mode & 0o077:
            raise SystemExit(f"--dest {d} has mode {st.st_mode & 0o777:o}: broader than 700, refused")
        if st.st_uid != os.getuid():
            raise SystemExit(f"--dest {d} is not owned by this user")
        if any(d.iterdir()) and not (d / WORK / "layout.json").is_file():
            raise SystemExit(f"--dest {d} holds something that is not a previous fetch's layout ({WORK}/layout.json missing): refused")
    else:
        d.mkdir(parents=True)
        os.chmod(d, 0o700)
    (d / WORK).mkdir(exist_ok=True)
    lay = d / WORK / "layout.json"
    if not lay.is_file():
        lay.write_text(json.dumps({"format": FORMAT}))
    return Path(os.path.realpath(d))


def _atomic_write(p: Path, text: str) -> None:
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, p)


def finished_dirs(store: Path) -> tuple[int, list[dict]]:
    """(runs in the store, the finished runs' directories): the done attempt of each done run, as the cut reads them. Paths, attempt ids and end times only."""
    con = sqlite3.connect(f"{store.as_uri()}?mode=ro&immutable=1", uri=True)
    try:
        n = con.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        rows = con.execute("SELECT DISTINCT a.run_dir, a.id, a.ended_utc FROM attempts a JOIN runs r USING(run_key)"
                           " WHERE r.status='done' AND a.state='done' AND a.run_dir IS NOT NULL ORDER BY a.run_dir").fetchall()
        bad = [r[0] for r in rows if not os.path.isabs(r[0])]
    finally:
        con.close()
    if bad:
        raise FetchError(f"{len(bad)} finished run directories are not absolute paths: they cannot be placed below --dest")
    return n, [{"run_dir": r[0], "attempt_id": r[1], "ended_utc": r[2]} for r in rows]


def local_dir(d: Path, run_dir: str) -> Path:
    return d / run_dir.lstrip("/")


def marker_path(d: Path, run_dir: str) -> Path:
    p = local_dir(d, run_dir)
    return p.with_name(p.name + MARK)


def measure(p: Path) -> tuple[int, int]:
    n = b = 0
    for f in p.rglob("*"):
        if f.is_file() and not f.is_symlink():
            n += 1
            b += f.stat().st_size
    return n, b


def marker_vouches(d: Path, e: dict) -> bool:
    """The marker beside this run directory exists and is for this very attempt, and the directory still has its file count and bytes."""
    m, ld = marker_path(d, e["run_dir"]), local_dir(d, e["run_dir"])
    try:
        rec = json.loads(m.read_text())
    except (OSError, ValueError):
        return False
    if not ld.is_dir() or not isinstance(rec, dict):
        return False
    same = rec.get("run_dir") == e["run_dir"] and rec.get("attempt_id") == e["attempt_id"] and rec.get("ended_utc") == e["ended_utc"]
    return same and (rec.get("files"), rec.get("bytes")) == measure(ld)


def _record(d: Path, rec: dict) -> None:
    """Amendment 30(l): copying during main is recorded. `fetch.json` is the last fetch; `.fetch/fetches.jsonl` keeps one line for each, as a rolling mirror fetches often."""
    _atomic_write(d / "fetch.json", json.dumps(rec, indent=1))
    with open(d / WORK / "fetches.jsonl", "a") as fh:
        fh.write(json.dumps(rec) + "\n")


def _rewrite_paths(new: Path, prefix: str, source: str) -> None:
    con = sqlite3.connect(str(new))
    try:
        with con:
            con.execute("UPDATE attempts SET run_dir = ? || run_dir WHERE run_dir IS NOT NULL", (prefix,))
            for k, v in (("fetch_run_dir_prefix", prefix), ("fetch_source", source)):
                con.execute("INSERT INTO meta(key,value,set_utc) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, set_utc=excluded.set_utc",
                            (k, v, _utc()))
    finally:
        con.close()
    for sfx in ("-wal", "-shm", "-journal"):
        if new.with_name(new.name + sfx).exists():
            raise FetchError(f"{new.name}{sfx} is left beside the rewritten copy")


def fetch(src_host: str, ssh: str, campaign_root: str, dest: Path, bwlimit_kib: int, *, min_free_gib: float = pull.MIN_FREE_GIB, src_tmp_dir: str = "/tmp",
          src_min_free_gib: float = 1.0, src_root: str = "/", src_python: str = "python3", timeout_s: float = 3600.0, tmp_name: str | None = None) -> dict:
    if bwlimit_kib <= 0:
        raise SystemExit("--bwlimit-kib is required and positive")
    d = prepare_dest(Path(dest))
    t0 = time.time()
    new = d / WORK / "state.sqlite.new"
    tmp = f"{src_tmp_dir.rstrip('/')}/{tmp_name or PREFIX + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:12] + '.sqlite'}"
    ssh_argv = shlex.split(ssh)
    may_exist, removed = False, None

    def remote(*args: str, **kw):
        return pull.run_group(ssh_argv + [src_host, shlex.join([src_python, "-", *args])], timeout_s, REMOTE)

    def cleanup() -> bool | None:
        """Removes the source's temporary copy, and only that. True removed or already gone, False it could not be."""
        try:
            r = remote("rm", tmp)
            return r.returncode == 0
        except BaseException:           # noqa: BLE001 -- a hung ssh: the caller names the path
            return False
    try:
        if shutil.disk_usage(d).free / 2**30 < min_free_gib:
            raise FetchError(f"refusing: under {min_free_gib:g} GiB free in {d} (--min-free-gib)")
        may_exist = True
        r = remote("copy", campaign_root, tmp, str(int(src_min_free_gib * 2**30)))
        if r.returncode == 1:
            may_exist = False       # the script refused before creating anything, or removed its own partial copy: never touch a file that was already there
        if r.returncode != 0:
            raise FetchError(f"the copy on {src_host} failed: {r.stderr.strip()[-300:]}")
        info = json.loads(r.stdout.strip().splitlines()[-1])
        if shutil.disk_usage(d).free < 2 * info["bytes"] + min_free_gib * 2**30:
            raise FetchError(f"refusing: {d} has too little free space for a {info['bytes']}-byte store and the floor of {min_free_gib:g} GiB")
        lst = d / WORK / "one.rel.txt"
        p = pull.run_group(["ionice", "-c3", "nice", "-n19", "rsync", "-a", "--no-owner", "--no-group", f"--bwlimit={bwlimit_kib}", "-e", ssh,
                            f"{src_host}:{tmp}", str(new)], timeout_s)
        if p.returncode != 0:
            raise FetchError(f"transfer of the store failed (rsync {p.returncode}): {p.stderr.strip()[-300:]}")
        if _sha256(new) != info["sha256"]:
            new.unlink()
            raise FetchError("the transferred store differs from the source's copy (sha256)")
        con = sqlite3.connect(f"{new.as_uri()}?mode=ro&immutable=1", uri=True)
        try:
            ok = con.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            con.close()
        if ok != "ok":
            new.unlink()
            raise FetchError(f"integrity_check on the transferred store: {ok}")
        removed = cleanup()
        may_exist = not removed
        runs, entries = finished_dirs(new)
        src = f"{src_host}:{src_root}"
        pulled = skipped = failed = 0
        for e in entries:
            if marker_vouches(d, e):
                skipped += 1
                continue
            m = marker_path(d, e["run_dir"])
            m.unlink(missing_ok=True)             # a marker that does not vouch for what is there is gone before anything is pulled
            if shutil.disk_usage(d).free / 2**30 < min_free_gib:
                raise FetchError(f"refusing: under {min_free_gib:g} GiB free in {d} (--min-free-gib), after {pulled} directories")
            try:
                p = pull.rsync_dir(e["run_dir"], src, str(d), bwlimit_kib, ssh, lst, timeout_s)
            except subprocess.TimeoutExpired:
                failed += 1
                continue
            ld = local_dir(d, e["run_dir"])
            if p.returncode != 0 or not ld.is_dir():
                failed += 1
                continue
            files, nbytes = measure(ld)
            _atomic_write(m, json.dumps({"run_dir": e["run_dir"], "attempt_id": e["attempt_id"], "ended_utc": e["ended_utc"], "files": files,
                                         "bytes": nbytes, "pulled_utc": _utc()}))
            pulled += 1
        rec = {"format": FORMAT, "src_host": src_host, "campaign_root": campaign_root, "src_root": src_root, "fetched_utc": _utc(), "store_sha256": info["sha256"],
               "store_bytes": info["bytes"], "store_copied_live": info["live"], "runs": runs, "finished_dirs": len(entries), "pulled": pulled,
               "skipped": skipped, "failed": failed, "dest": str(d), "store_replaced": failed == 0, "bwlimit_kib": bwlimit_kib, "priority": PRIORITY,
               "seconds": round(time.time() - t0, 1)}
        if failed:
            _record(d, rec)
            raise FetchError(f"{failed} of {len(entries)} finished run directories could not be pulled (pulled {pulled}, skipped {skipped}): "
                             f"D/state.sqlite is left as it was; the next fetch retries them")
        _rewrite_paths(new, str(d), f"{src_host}:{campaign_root}")
        with open(new, "rb") as fh:
            os.fsync(fh.fileno())
        os.replace(new, d / "state.sqlite")
        rec["seconds"] = round(time.time() - t0, 1)
        _record(d, rec)
        rec["tmp_left"] = None if removed else f"{src_host}:{tmp}"          # a success that could not remove the temporary copy says where it is
        return rec
    except FetchError as e:
        if may_exist:
            removed = cleanup() if removed is None or not removed else removed
            e.tmp, e.removed = f"{src_host}:{tmp}", bool(removed)
        raise
    except BaseException as e:
        if may_exist:
            removed = cleanup()
            raise FetchError(f"{type(e).__name__}: {e}", f"{src_host}:{tmp}", bool(removed)) from e
        raise


def main(argv_=None) -> int:
    ap = argparse.ArgumentParser(prog="snapshot.fetch", description="Fetch the campaign's store and its finished runs' directories into one local directory; see the module docstring.")
    ap.add_argument("--src-host", required=True, help="user@host of the run host")
    ap.add_argument("--ssh", required=True, help="the ssh command, as rsync -e takes it (no default: a key is not guessed)")
    ap.add_argument("--campaign-root", required=True, help="the campaign root ON THE SOURCE HOST (state.sqlite and runs/ below it)")
    ap.add_argument("--dest", required=True, type=Path, help="D: created 700; the same directory can be fetched into again and again")
    ap.add_argument("--bwlimit-kib", required=True, type=int)
    ap.add_argument("--min-free-gib", type=float, default=pull.MIN_FREE_GIB)
    ap.add_argument("--src-tmp-dir", default="/tmp", help="on the source: where the temporary store copy is made (not inside the campaign root)")
    ap.add_argument("--src-min-free-gib", type=float, default=1.0, help="on the source: free space to keep beyond 2 x the store")
    ap.add_argument("--src-root", default="/", help="the root the recorded run directories are absolute from, on the source")
    ap.add_argument("--src-python", default="python3")
    ap.add_argument("--timeout-s", type=float, default=3600.0, help="per ssh or rsync call")
    a = ap.parse_args(argv_)
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(SystemExit(143)))
    try:
        rec = fetch(a.src_host, a.ssh, a.campaign_root, a.dest, a.bwlimit_kib, min_free_gib=a.min_free_gib, src_tmp_dir=a.src_tmp_dir,
                    src_min_free_gib=a.src_min_free_gib, src_root=a.src_root, src_python=a.src_python, timeout_s=a.timeout_s)
    except FetchError as e:
        left = "" if e.tmp is None else f"; temporary copy on the source: {e.tmp} ({'removed' if e.removed else 'NOT removed: remove it by hand'})"
        print(f"fetch FAILED: {e}{left}", file=sys.stderr)
        return 1
    if rec["tmp_left"]:
        print(f"fetch: warning: the temporary copy on the source was NOT removed: {rec['tmp_left']} (remove it by hand)", file=sys.stderr)
    print(f"fetch ok runs={rec['runs']} finished_dirs={rec['finished_dirs']} pulled={rec['pulled']} skipped={rec['skipped']} store_bytes={rec['store_bytes']} "
          f"seconds={rec['seconds']} dest={rec['dest']}")
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
