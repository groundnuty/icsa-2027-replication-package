"""A per-run cache of the frozen pipeline's per-run result, filled during the main block, so that a snapshot only assembles.

`icsa.pipeline.postrun.run_pipeline` labels, scores and codes every run, which is the slow part (a reference per instance, a trace
per run); the files it writes need every run's result. This module keeps each run's result (a `postrun.Processed`) on disk, keyed by
what the result depends on, so that a snapshot taken later recomputes only the runs that are missing or whose inputs changed.

    python -m snapshot.pcache fill     --campaign-root D --cache C [--max-runs N] [--jobs J] ...   # during the block, on the fetch mirror D
    python -m snapshot.pcache assemble --cut CUT --cache C --out OUT [--jobs J] ...                # what `snapshot --pipeline-cache C` does

The one rule: the frozen `run_pipeline` writes every output, always. The cache only stands in for `process_run` (the per-run call) on a
key hit; it never re-implements a line of what `run_pipeline` does with the results (the Batch, causes.csv, the second coder's sample,
infra.json, none_counts.json, the manifest). So a cached snapshot is the frozen pipeline's output byte for byte, or the test that says
so fails.

A key (`entry_key`) holds: the run's export row, its exclude flag, the code (the live source tree, the tree's data/, the pipeline packages, the
parser's version as `score_run` records it, this file, the interpreter and the numeric libraries), the resources (`resources_identity`: an
injected one says what it is; `Production` is read from its paths, the full layout index's bytes, every S1 daily file the resolver lists (name,
size, mtime), the published-fields file and the cell-mask file the instances manifest names (size, mtime); anything else is refused), the
per-run address-space limit (`rlimit_as_gib`: None when `jobs` <= 1, else `worker_gib`, what `_init_worker` applies to each worker; the pool's
size changes no byte of an output, so it is not keyed) and a fingerprint of the run directory. A run whose code, resources, limit or files
changed has a new key, so its old entry is never read.

The fingerprint hashes every file of up to SMALL_BYTES (1 MiB) by content and every larger one by (size, mtime_ns), with the relative path of
each. That is the stated limit of the key: a change inside a file over a mebibyte that keeps its size and mtime goes unseen. A run is
UNCACHEABLE, and so never cached by `fill` and always computed by `assemble`, when its directory holds a symlink anywhere (a link can reach a
file outside the directory that the fingerprint does not read), or when its run record names a path outside it (`code_cells_path` or
`output_dir`, absolute or with a `..` part, which `process_run` joins to the run dir). A record that cannot be read decides nothing here: the
pipeline fails such a run, and a failure is never cached. `assemble` looks at the run directory again just before it serves an entry, and
computes the run instead if it changed (or became uncacheable) since the plan was made. Before the pipeline runs, `assemble` also refuses
(`PlannedMissLimit`, nothing written to --out) more planned misses than max(MISS_LIMIT_MIN, ceil(MISS_LIMIT_SHARE * analysed runs)), or than
--max-planned-misses (-1: no limit), not counting runs that the last fill's failures.json lists: a cache that misses most runs belongs to another
code, data, limit or mirror, and a cold pass is not what was asked for.

Layout of the cache directory C (mode 0700, ours; one that is broader or not ours is refused, because entries are pickles; one inside the
campaign tree or inside any attempt directory is refused before anything is made):
    entries/<key[:2]>/<key>.pkl    {"format", "key", "processed"}, written beside its final name, then renamed
    fill.lock                      one `fill` at a time (flock); a second one returns {"busy": True}
    last_fill.json                 the last fill's counts, no run keys
    failures.json                  the last fill's failed runs (block, run_key, reason, detail): sealed like the cache
Both commands read a private copy of the store, in a temporary directory that is removed afterwards (under a snapshot, TMPDIR is inside
--out), never the store in place: a read-only open of a quiescent WAL-mode store creates -wal and -shm beside it.
Failures are never cached: a failing run is run again by every fill and every assemble, and listed in the manifest as always.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True      # before anything else is imported: a .pyc written beside the source is a write outside --out

import argparse                     # noqa: E402
import fcntl                        # noqa: E402
import hashlib                      # noqa: E402
import json                         # noqa: E402
import math                         # noqa: E402
import os                           # noqa: E402
import pickle                       # noqa: E402
import secrets                      # noqa: E402
import sqlite3                      # noqa: E402
import stat                         # noqa: E402
import tempfile                     # noqa: E402
import time                         # noqa: E402
from pathlib import Path           # noqa: E402

from icsa import codestamp, paths   # noqa: E402
from icsa.campaign.export import export_infra   # noqa: E402
from icsa.campaign.store import Store   # noqa: E402
from icsa.pipeline import postrun   # noqa: E402
from icsa.pipeline.loadrec import RECORD_FILES, PipelineError   # noqa: E402
from icsa.pipeline.resources import Production   # noqa: E402
from icsa.scoring import parser_version as _parser_version   # noqa: E402

from . import cut as cutmod         # noqa: E402
from .codecheck import tree_data_hash   # noqa: E402,F401 -- here since the cache key was first to use it; snapshot/codecheck.py owns it

FORMAT = "icsa-pcache-v1"
INDEX_FILES = ("digest.json", "ids.json", "index.npz")      # what `fullindex.load_full_index` reads from `index_dir`
MISS_LIMIT_MIN = 20             # `assemble` refuses more unexplained planned misses than max(MISS_LIMIT_MIN, ceil(MISS_LIMIT_SHARE * analysed runs))
MISS_LIMIT_SHARE = 0.10
SMALL_BYTES = 1 << 20           # a run-dir file of up to this size is fingerprinted by its content, a larger one by (size, mtime_ns)

# What the last `assemble` did to the runs, in this process. With `jobs` > 1 the wrapper runs in forked workers and these do not see it.
CALLS: list[tuple[str, str]] = []        # (block, key) of every run `assemble` computed instead of loading
COUNTERS = {"hit": 0, "miss": 0, "unreadable": 0, "changed_at_use": 0}


class PcacheError(RuntimeError):
    """The cache directory cannot be used (not ours, too open, not a directory), or a path is where this tool never writes."""


class PlannedMissLimit(PcacheError):
    """More planned misses that nothing explains than the limit allows: the cache does not belong to this host's code, data, limits or mirror."""

    def __init__(self, misses: int, unexplained: int, limit: int):
        super().__init__(f"planned_misses={misses} (unexplained {unexplained}) above the limit {limit}")
        self.misses, self.unexplained, self.limit = misses, unexplained, limit


# ---- identities and keys ------------------------------------------------------------------------------------------------------------

def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def code_identity() -> dict:
    """What the code is, computed from the packages that are running, never from a `.code-stamp.json` (a stamp can be older than the files).
    The tree's `data/` is in it too: the pipeline reads it and the code stamp does not cover it."""
    import icsa
    import numpy
    import pandas
    repo_root = Path(icsa.__file__).resolve().parents[1]
    return {"tree_sha256": codestamp.tree_hash(repo_root), "tree_data_sha256": tree_data_hash(repo_root),
            "pipeline_hashes": {p: postrun.tree_hash(p) for p in postrun.HASHED},
            "parser_version": _parser_version.parser_version(),         # score_run writes it into every scored row; its commit depends on git being there
            "pcache_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "python": sys.version, "numpy": numpy.__version__, "pandas": pandas.__version__}


def _path_or_none(x) -> str | None:
    return None if x is None else str(Path(x).resolve())


def _stat_or_none(p: Path) -> list[int] | None:
    try:
        st = p.stat()
    except OSError:
        return None
    return [st.st_size, st.st_mtime_ns]


def _file_identity(p: Path) -> dict:
    """A file too big to hash (the published fields are 1.8 GB) by where it is and its size and mtime."""
    return {"path": str(p.resolve()), "stat": _stat_or_none(p)}


def _instances_manifest_path() -> Path:
    """Where `oracle_real.load_truth` reads the instances manifest: the running tree's data/instances/instances.json."""
    import icsa
    return Path(icsa.__file__).resolve().parents[1] / "data" / "instances" / "instances.json"


def _cell_masks_identity() -> dict:
    """The truth masks, as `load_truth` finds them: the file the manifest names (an absolute path, not under DATA_ROOT)."""
    try:
        p = Path(json.loads(_instances_manifest_path().read_text())["cell_masks"]["file"])
    except (OSError, ValueError, KeyError, TypeError) as e:
        return {"error": type(e).__name__}
    return _file_identity(p)


def _s1_files_identity(data_dir) -> str:
    """sha256 over (file name, size, mtime) of every S1 daily file the resolver lists, in `icsa/refdet/fieldcache.py`'s `s1_fingerprint` pattern but
    over every day, which is a superset of what any one reference reads. A directory the resolver cannot read, or one with two files for a date,
    gives an error value: a key that differs from every good one, and the runs computed under it fail as they would anyway."""
    from icsa.refdet import data as rdata
    d = Path(data_dir)
    try:
        index = rdata.s1_index(d)
        h = hashlib.sha256(str(d.resolve()).encode())
        for _, f in sorted(index.items()):
            st = f.stat()
            h.update(f"\n{f.name} {st.st_size} {st.st_mtime_ns}".encode())
    except Exception as e:      # noqa: BLE001 -- sound: the value differs, and nothing is cached under it that a good directory would serve
        return f"error:{type(e).__name__}"
    return h.hexdigest()


def resources_identity(res) -> dict:
    """What the resources are. An injected `Resources` that has a callable `pcache_identity()` says so itself; `Production` is its paths, the
    bytes of the full layout index, the S1 daily files (name, size, mtime), the published-fields file (`refdet.data`'s own resolver; size and
    mtime) and the cell-mask file the instances manifest names (size and mtime, the way `load_truth` finds it). Any other class gives no sound
    key, so it is refused: a key on the class name alone would serve one resources' results to another."""
    f = getattr(res, "pcache_identity", None)
    if callable(f):
        t = type(res)
        return {**f(), "class": f"{t.__module__}.{t.__qualname__}"}
    if isinstance(res, Production):
        from icsa.instruments import fullindex
        from icsa.refdet import data as rdata
        d = fullindex.index_dir(res.index_root)
        # the index directory the pipeline loads, not --index-root as spelled: omitted and given as the data root are one input, so one key
        return {"class": "Production", "index_dir": str(d.resolve()), "s1_dir_name": str(res.s1_dir_name),
                "mount_root": _path_or_none(res.mount_root), "data_dir": _path_or_none(res.data_dir),
                "full_index": {n: _sha256_file(d / n) if (d / n).is_file() else None for n in INDEX_FILES},
                "data_root": str(Path(paths.DATA_ROOT).resolve()),
                "supp_file": _file_identity(rdata._ref("data", rdata.SUPP_NAME)),
                "cell_masks": _cell_masks_identity(),
                "s1_files": _s1_files_identity(res.data_dir)}
    raise TypeError(f"no cache identity for {type(res).__qualname__}: give it a pcache_identity() method")


def _raise(err: OSError) -> None:
    raise err


def _outside(v) -> bool:
    return isinstance(v, str) and (os.path.isabs(v) or ".." in Path(v).parts)


def _record_names_outside(root: str) -> bool:
    """Whether the run record (the first existing of `loadrec.RECORD_FILES`, as `read_record` takes it) names a path outside the run dir. A record
    that cannot be read decides nothing: the pipeline fails the run, and a failure is never cached."""
    for name in RECORD_FILES:
        p = Path(root) / name
        if p.is_file():
            try:
                rec = json.loads(p.read_text())
            except (OSError, ValueError):
                return False
            return isinstance(rec, dict) and any(_outside(rec.get(k)) for k in ("code_cells_path", "output_dir"))
    return False


def fingerprint_and_reason(run_dir) -> tuple[str | None, str | None]:
    """(fingerprint, None), or (None, why) when the run cannot be cached: "symlink" (any link anywhere under the run dir, never followed) or
    "external_path" (the record names a path outside the run dir). The fingerprint is a sha256 over every regular file's relative path and size
    with its content hash (up to SMALL_BYTES) or its mtime_ns (larger). A missing directory is ("missing", None). An unreadable one raises OSError."""
    if not run_dir or not os.path.isdir(run_dir):
        return "missing", None
    root = str(run_dir)
    items: list[list] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False, onerror=_raise):
        for name in dirnames + filenames:
            full = os.path.join(dirpath, name)
            st = os.lstat(full)
            if stat.S_ISLNK(st.st_mode):
                return None, "symlink"
            if stat.S_ISREG(st.st_mode):
                rel = Path(os.path.relpath(full, root)).as_posix()
                items.append([rel, st.st_size, _sha256_file(Path(full)) if st.st_size <= SMALL_BYTES else st.st_mtime_ns])
    if _record_names_outside(root):
        return None, "external_path"
    items.sort(key=json.dumps)
    return hashlib.sha256(json.dumps(items).encode()).hexdigest(), None


def run_dir_fingerprint(run_dir) -> str | None:
    """The fingerprint, or None when the run is uncacheable (`fingerprint_and_reason`)."""
    return fingerprint_and_reason(run_dir)[0]


def uncacheable_reason(run_dir) -> str | None:
    """"symlink", "external_path", or None when the run can be cached."""
    return fingerprint_and_reason(run_dir)[1]


def _rlimit_as_gib(jobs: int, worker_gib: int) -> int | None:
    """What `postrun._init_worker` applies to each run: an address-space limit with a pool, none without."""
    return None if jobs <= 1 else worker_gib


def entry_key(entry: dict, store_row, code_id: dict, res_id: dict, fingerprint: str, rlimit_as_gib: int | None) -> str:
    return hashlib.sha256(postrun.dumps({"format": FORMAT, "entry": entry, "exclude_from_analysis": bool(store_row["exclude_from_analysis"]),
                                         "code": code_id, "resources": res_id, "rlimit_as_gib": rlimit_as_gib,
                                         "run_dir": fingerprint}).encode()).hexdigest()


# ---- the directory ------------------------------------------------------------------------------------------------------------------

def _entry_path(cache: Path, key: str) -> Path:
    return Path(cache) / "entries" / key[:2] / f"{key}.pkl"


def _open_cache(cache: Path, create: bool) -> bool:
    """Whether the cache directory exists, after checking that it is ours and closed to others. `create`: make it, mode 0700, if it is not there."""
    try:
        st = os.stat(cache)
    except FileNotFoundError:
        if not create:
            return False
        Path(cache).mkdir(parents=True)
        os.chmod(cache, 0o700)
        return True
    if not stat.S_ISDIR(st.st_mode):
        raise PcacheError(f"{cache} is not a directory")
    if st.st_uid != os.getuid():
        raise PcacheError(f"{cache} is not owned by this user: its entries are pickles and are never read from a directory another user owns")
    if st.st_mode & 0o077:
        raise PcacheError(f"{cache} has mode {oct(st.st_mode & 0o777)}, broader than 0700: its entries are pickles")
    return True


def _remove_tree(root: Path) -> None:
    """Remove a private temporary directory, by full paths. Not `shutil.rmtree`: that unlinks by name relative to a directory descriptor, which the
    snapshot's write guard (an audit hook) cannot place and so refuses."""
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        for name in filenames:
            try:
                os.remove(os.path.join(dirpath, name))
            except OSError:
                pass
        for name in dirnames:
            try:
                os.rmdir(os.path.join(dirpath, name))
            except OSError:
                pass
    try:
        os.rmdir(root)
    except OSError:
        pass


def _write_atomic(path: Path, data: bytes) -> None:
    """Written beside its final name, then renamed, so a reader sees all of a file or none of it."""
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _write_entry(cache: Path, key: str, processed) -> None:
    path = _entry_path(cache, key)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _write_atomic(path, pickle.dumps({"format": FORMAT, "key": key, "processed": processed}, protocol=5))


def load_entry(path, key: str):
    """The cached `Processed`, only if the file is this format and holds this key; None on anything else, a read or unpickle error included."""
    try:
        with open(path, "rb") as fh:
            o = pickle.load(fh)
        if isinstance(o, dict) and o.get("format") == FORMAT and o.get("key") == key and isinstance(o.get("processed"), postrun.Processed):
            return o["processed"]
    except Exception:       # noqa: BLE001 -- an entry that cannot be read is a miss, not a failure: the run is computed
        pass
    return None


def _read_store(db: Path, res):
    """The way `run_pipeline` reads it: the export's analysed attempts, each run's flags, and every attempt's directory (discarded ones too)."""
    store = postrun.ReadOnlyStore(db)
    try:
        export = export_infra(store, res.instances())
        flags_of = {r["run_key"]: r for r in store.q("SELECT run_key, exclude_from_analysis FROM runs")}
        attempt_dirs = [r["run_dir"] for r in store.q("SELECT run_dir FROM attempts") if r["run_dir"]]
    finally:
        store.close()
    return export, flags_of, attempt_dirs


def _refuse_inside(path: Path, roots, what: str) -> None:
    """`path` (resolved, existing or not) must be neither equal to nor inside any of `roots`."""
    here = Path(path).resolve()
    for r in roots:
        rd = Path(r).resolve()
        if here == rd or rd in here.parents:
            raise PcacheError(f"{what} {path} is inside {rd}: this tool never writes into a campaign tree or a run directory")


def _sorted_entries(export: dict) -> list[dict]:
    """Exactly `run_pipeline`'s order."""
    return sorted(export["analysed_attempts"], key=lambda e: (e["key"].split("__")[0], e["block"], e["run_key"]))


# ---- fill ---------------------------------------------------------------------------------------------------------------------------

def fill(campaign_root, cache_dir, res, *, jobs: int = 1, worker_gib: int = 8, max_runs: int | None = None) -> dict:
    """Process the campaign's runs that the cache lacks, with the frozen machinery (`postrun._process_all`, so `jobs` and `worker_gib` mean what
    they mean there), and keep each result. Returns (and writes to last_fill.json) counts only:
      entries      the campaign's analysed attempts          hits         of them already in the cache
      todo         the ones missing                          uncacheable  not cacheable at all (symlink, external_path): never processed here
      processed    of the todo, taken on by this call: the first `max_runs` in `run_pipeline`'s order
      cached       written                                   failed       listed in failures.json, never cached
      changed      processed, but their run directory changed meanwhile: not cached (the next fill takes them)
    hits + todo + uncacheable = entries, and processed = cached + failed + changed. `uncacheable_by_reason` says which. `{"busy": True}` and
    nothing done when another fill holds the lock.
    The store is never opened where it is: a private copy is read, brought to the current schema as the cut's own copy is, in a temporary
    directory that is removed again. A cache inside the campaign tree or inside any attempt directory is refused before it is created."""
    if max_runs is not None and max_runs < 0:
        raise ValueError("max_runs must not be negative")
    t0 = time.monotonic()
    campaign_root, cache = Path(campaign_root), Path(cache_dir)
    _refuse_inside(cache, [campaign_root], "cache")
    tmp = Path(tempfile.mkdtemp(prefix="pcache-store-"))        # mode 0700, and not under the cache
    try:
        copy = tmp / "state.sqlite"
        cutmod.copy_store(campaign_root / "state.sqlite", copy)
        Store(copy).close()          # the private copy brought to the current schema, as the cut's `Store` open brings its own (snapshot/cut.py)
        export, flags_of, attempt_dirs = _read_store(copy, res)
    finally:
        _remove_tree(tmp)
    _refuse_inside(cache, attempt_dirs, "cache")
    _open_cache(cache, create=True)
    (cache / "entries").mkdir(mode=0o700, exist_ok=True)
    fd = os.open(cache / "fill.lock", os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"busy": True}
        return _fill_locked(export, flags_of, cache, res, jobs, worker_gib, max_runs, t0)
    finally:
        os.close(fd)        # the lock goes with the descriptor


def _fill_locked(export: dict, flags_of, cache: Path, res, jobs: int, worker_gib: int, max_runs: int | None, t0: float) -> dict:
    entries = _sorted_entries(export)
    code_id, res_id, limit = code_identity(), resources_identity(res), _rlimit_as_gib(jobs, worker_gib)
    hits, uncacheable, todo = 0, {}, []                  # todo: (entry, fingerprint or None, key or None, the OSError or None)
    failed: list[dict] = []
    for e in entries:
        try:
            fp, why = fingerprint_and_reason(e["run_dir"])
        except OSError as err:                           # a directory that cannot be listed: the run is listed, not cached
            todo.append((e, None, None, err))
            continue
        if fp is None:
            uncacheable[why] = uncacheable.get(why, 0) + 1
            continue
        key = entry_key(e, flags_of[e["run_key"]], code_id, res_id, fp, limit)
        if _entry_path(cache, key).is_file():
            hits += 1
        else:
            todo.append((e, fp, key, None))
    taken = todo if max_runs is None else todo[:max_runs]
    runnable = {}
    for e, fp, key, err in taken:
        if err is not None:
            failed.append(postrun._failure(e, "error:fingerprint", f"{type(err).__name__}: {err}"[:300]))
        else:
            runnable.setdefault((e["block"], e["key"]), (e, fp, key))
    groups = postrun._by_instance([v[0] for v in runnable.values()])
    cached = changed = 0
    for g_done, g_failed in postrun._process_all(groups, flags_of, res, jobs, worker_gib):
        failed += g_failed
        for k, p in g_done.items():
            e, fp, key = runnable[k]
            try:
                now = run_dir_fingerprint(e["run_dir"])
            except OSError:
                now = None
            if now != fp:                                # changed while it was processed, or no longer cacheable
                changed += 1
                continue
            _write_entry(cache, key, p)
            cached += 1
    failures = sorted(({"block": f["block"], "run_key": f["run_key"], "reason": f["reason"], "detail": f["detail"]} for f in failed),
                      key=lambda f: (f["block"], f["run_key"]))
    _write_atomic(cache / "failures.json", (json.dumps(failures, indent=1) + "\n").encode())
    counts = {"format": FORMAT, "entries": len(entries), "hits": hits, "todo": len(todo), "uncacheable": sum(uncacheable.values()),
              "uncacheable_by_reason": dict(sorted(uncacheable.items())), "processed": len(taken), "cached": cached,
              "failed": len(failed), "changed": changed, "groups": len(groups), "seconds": round(time.monotonic() - t0, 3)}
    _write_atomic(cache / "last_fill.json", (json.dumps(counts, indent=1, sort_keys=True) + "\n").encode())
    return counts


# ---- assemble -----------------------------------------------------------------------------------------------------------------------

def _failed_runs(cache: Path) -> set[tuple[str, str]]:
    """The (block, run_key) pairs the last fill listed in failures.json: runs that failed there, so are never cached. Unreadable: none."""
    try:
        return {(f["block"], f["run_key"]) for f in json.loads((Path(cache) / "failures.json").read_text())}
    except (OSError, ValueError, KeyError, TypeError):
        return set()


def assemble(cut_root, cache_dir, out, res, *, jobs: int = 1, worker_gib: int = 8, max_planned_misses: int | None = None) -> dict:
    """The frozen `run_pipeline` over the cut, with `process_run` standing in for the cache: a run whose key has an entry is loaded, any other is
    computed by the original. Writes nothing into `cache_dir` (a snapshot's write guard refuses a write outside its --out), takes no lock and
    makes no directory there. A `cache_dir` that does not exist makes every run a miss, which is still correct.

    The cut's store is copied (`cut.copy_store`, which makes nothing beside it) into a temporary directory, and both the plan and the frozen
    `run_pipeline` read that copy; no schema migration is done, so the pipeline sees the store exactly as a cold run would. An `out` that is the
    cut's directory, inside it, or inside any attempt directory is refused (`PcacheError`) before anything is written, since `run_pipeline`'s
    own check would now compare it with the copy's directory.

    Before the pipeline runs, planned misses that the last fill's failures.json does not list ("unexplained": a run that failed there is always a
    miss) are counted against a limit, max(MISS_LIMIT_MIN, ceil(MISS_LIMIT_SHARE * analysed runs)), or `max_planned_misses` if given (-1: no
    limit). More than the limit raises `PlannedMissLimit` (a `PcacheError`) with nothing written to `out`: a cache that misses most runs does not
    belong to this host's code, data, limits or mirror, and a cold pass over them is not what was asked for.

    Returns {"manifest": run_pipeline's manifest, "pcache": {...}}. `planned_hits` and `planned_misses` are what the keys say before the
    pipeline runs, `planned_uncacheable` of the misses are runs that cannot be cached (they count as unexplained), `planned_unexplained_misses` and
    `planned_miss_limit` (None: switched off) are the limit's two sides. With `jobs` == 1 the pipeline's own counters add
    `hits`, `misses` (every run computed, unreadable entries and changed ones included), `unreadable` (a file was there and could not be used)
    and `changed_at_use` (the run directory differed from the plan when the entry was about to be served), and `CALLS` lists the (block, key) of
    each run computed. With `jobs` > 1 the wrapper runs in forked workers, whose counters this process cannot see, so those keys are left out."""
    cut_root, cache, out = Path(cut_root), Path(cache_dir), Path(out)
    CALLS.clear()
    for k in COUNTERS:
        COUNTERS[k] = 0
    if max_planned_misses is not None and max_planned_misses < -1:
        raise ValueError("max_planned_misses is a count, or -1 for no limit")
    exists = _open_cache(cache, create=False)
    tmp = Path(tempfile.mkdtemp(prefix="pcache-cut-"))     # under a snapshot, TMPDIR is inside --out: the copy is inside the write guard
    try:
        cutmod.copy_store(cut_root / "state.sqlite", tmp / "state.sqlite")
        export, flags_of, attempt_dirs = _read_store(tmp / "state.sqlite", res)
        _refuse_inside(out, [cut_root, *attempt_dirs], "out")
        t0 = time.monotonic()
        code_id, res_id, limit = code_identity(), resources_identity(res), _rlimit_as_gib(jobs, worker_gib)
        plan: dict[tuple, tuple[str | None, Path | None, str | None]] = {}
        planned_hits = planned_misses = planned_uncacheable = unexplained = 0
        failed_runs = _failed_runs(cache) if exists else set()
        for e in export["analysed_attempts"]:
            key = path = fp = None
            try:
                fp, why = fingerprint_and_reason(e["run_dir"])
                planned_uncacheable += why is not None
            except OSError:                              # a directory that cannot be listed: computed, so that it fails the way it always does
                pass
            if fp is not None:
                key = entry_key(e, flags_of[e["run_key"]], code_id, res_id, fp, limit)
                path = _entry_path(cache, key) if exists else None
                path = path if path is not None and path.is_file() else None
            plan[(e["block"], e["key"], e["run_dir"], e["attempt"])] = (key, path, fp)
            planned_hits += path is not None
            planned_misses += path is None
            unexplained += path is None and (e["block"], e["key"]) not in failed_runs
        fingerprint_seconds = time.monotonic() - t0
        if max_planned_misses is None:
            limit_misses = max(MISS_LIMIT_MIN, math.ceil(MISS_LIMIT_SHARE * len(export["analysed_attempts"])))
        else:
            limit_misses = None if max_planned_misses == -1 else max_planned_misses
        if limit_misses is not None and unexplained > limit_misses:
            raise PlannedMissLimit(planned_misses, unexplained, limit_misses)

        original = postrun.process_run

        def cached_process_run(entry, store_row, res_):
            key, path, fp = plan.get((entry["block"], entry["key"], entry["run_dir"], entry["attempt"]), (None, None, None))
            if path is not None:
                try:
                    now = run_dir_fingerprint(entry["run_dir"])        # the plan was made earlier: look again before serving
                except OSError:
                    now = None
                if now == fp:
                    p = load_entry(path, key)
                    if p is not None:
                        COUNTERS["hit"] += 1
                        return p
                    COUNTERS["unreadable"] += 1
                else:
                    COUNTERS["changed_at_use"] += 1
            COUNTERS["miss"] += 1
            CALLS.append((entry["block"], entry["key"]))
            return original(entry, store_row, res_)

        t1 = time.monotonic()
        postrun.process_run = cached_process_run        # `_process_group` looks it up as a module global at call time; a forked worker inherits it
        try:
            manifest = postrun.run_pipeline(tmp, out, res, jobs=jobs, worker_gib=worker_gib)
        finally:
            postrun.process_run = original
    finally:
        _remove_tree(tmp)
    info = {"planned_hits": planned_hits, "planned_misses": planned_misses, "planned_uncacheable": planned_uncacheable,
            "planned_unexplained_misses": unexplained, "planned_miss_limit": limit_misses,
            "fingerprint_seconds": round(fingerprint_seconds, 3), "pipeline_seconds": round(time.monotonic() - t1, 3)}
    if jobs <= 1:
        info.update(hits=COUNTERS["hit"], misses=COUNTERS["miss"], unreadable=COUNTERS["unreadable"], changed_at_use=COUNTERS["changed_at_use"])
    return {"manifest": manifest, "pcache": info}


# ---- command line -------------------------------------------------------------------------------------------------------------------

def _production(ns):
    return Production(Path(ns.index_root) if ns.index_root else None, ns.s1_dir, Path(ns.mount_root) if ns.mount_root else None,
                      Path(ns.data_dir) if ns.data_dir else None)


def main(argv=None, resources=None) -> int:
    """`resources`: injected by the tests; the command line builds `Production` from its options, as `snapshot` does."""
    ap = argparse.ArgumentParser(prog="python -m snapshot.pcache", description=__doc__.split("\n\n")[0])
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--index-root", default=None)
    common.add_argument("--data-dir", default=None)
    common.add_argument("--s1-dir", default="s1z")
    common.add_argument("--mount-root", default=None)
    common.add_argument("--jobs", type=int, default=1)
    common.add_argument("--worker-gib", type=int, default=8)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fill", parents=[common], help="process the runs the cache lacks, keep each result")
    f.add_argument("--campaign-root", required=True, type=Path, help="holds state.sqlite (the fetch mirror); the store is copied, never opened in place")
    f.add_argument("--cache", required=True, type=Path)
    f.add_argument("--max-runs", type=int, default=None, help="process at most this many missing runs in this call")
    a = sub.add_parser("assemble", parents=[common], help="the frozen pipeline over a cut, loading each run's result from the cache")
    a.add_argument("--cut", required=True, type=Path, help="holds state.sqlite")
    a.add_argument("--cache", required=True, type=Path)
    a.add_argument("--out", required=True, type=Path)
    a.add_argument("--max-planned-misses", type=int, default=None,
                   help="refuse (exit 2) more planned misses than this that the last fill's failures.json does not explain; -1: no limit; "
                        f"default max({MISS_LIMIT_MIN}, ceil({MISS_LIMIT_SHARE} * analysed runs))")
    ns = ap.parse_args(argv)
    res = resources or _production(ns)
    try:
        if ns.cmd == "fill":
            r = fill(ns.campaign_root, ns.cache, res, jobs=ns.jobs, worker_gib=ns.worker_gib, max_runs=ns.max_runs)
            if r.get("busy"):
                print("pcache fill busy")
                return 0
            print("pcache fill " + " ".join(f"{k}={r[k]}" for k in ("entries", "hits", "todo", "uncacheable", "processed", "cached", "failed", "changed", "groups", "seconds")))
            return 1 if r["failed"] else 0
        r = assemble(ns.cut, ns.cache, ns.out, res, jobs=ns.jobs, worker_gib=ns.worker_gib, max_planned_misses=ns.max_planned_misses)
    except (cutmod.CutError, PipelineError, PcacheError, sqlite3.Error) as e:
        print(f"pcache {ns.cmd} FAILED {type(e).__name__}: {str(e)[:200]}", file=sys.stderr)
        return 2
    m, c = r["manifest"], r["pcache"]
    sha = hashlib.sha256((ns.out / "manifest.json").read_bytes()).hexdigest()[:16]
    print(f"pcache assemble scored={m['counts']['scored']} failed={m['counts']['failed']} planned_hits={c['planned_hits']} "
          f"planned_misses={c['planned_misses']} manifest={sha}")
    return 1 if m["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
