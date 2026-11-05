"""Per-day truth for H3's agent-run measure: each finished attempt relabelled with the FROZEN labeller, the day-by-day coverage of what the run fetched, was
delivered, read and analysed written beside it.

The pipeline keeps no per-day extent (`postrun.process_run` slims the evidence: "no extents"), and the stricter readings of the measure need them. So this job runs
`icsa.instruments.labeller.label_run`, imported unchanged, on each attempt in the mirror, fed as `postrun.process_run` feeds it (the cells the sandbox logged, else the
harness's `code_cells.json`; a run whose tracer never started is `unknown` with no extents and calls nothing). It reads only the run directory, the local full layout
index and the reference on the local S1 copy, never the network.

    python -m icsa.faults.mainaudit.daytruth MIRROR --out DIR [--workers N] [--blocks main,pilot] [--retry-failed]
        [--index-root DIR] [--data-dir DIR] [--s1-dir NAME] [--mount-root PATH] [--worker-gib G]

The outputs are SEALED: nobody reads them until the measure is frozen, so the one line printed is `daytruth: processed N, skipped M (done), failed F`. No label, coverage,
option or count of one is ever printed (nor returned from a worker: a worker writes its file and says nothing).

Output: `DIR/<run_key>/<attempt>.json` (`daytruth/1`), `DIR` mode 0700, each run's directory 0700, each file 0600, each written by rename. `<run_key>` is the run
directory's name with its block, `<attempt>` the attempt directory's (`attempt1.try1`). The JSON:
    schema, run_key, block, attempt, attempt_dir, option, layout, instance, label (the instrument's, `RunLabel.label`, after amendment 19(a)'s route), no_trace,
    required_days (sorted day indices with any required cell, baseline and target),
    coverage {source: {day: fraction of that day's required cells the source holds}}, only days above 0 (absent = 0), for fetched, delivered, read (each present only
        where the labeller observed it: an absent key is "not observed", `{}` is "observed, covered nothing") and analysed (`RunLabel.analysed`, A_lo, what scoring takes),
    touched_days {source: [days]} for fetched and delivered, present where the source is: the days of every FILE the source moved a byte of, whether or not a byte falls on a
        required cell (a header, or a read outside the box, opens the file: what a file-level record, the audit or D's gate, sees; the coverage cannot say it). Re-read from the
        log the labeller names in `observed`, with the labeller's own readers, and checked: the extent of the re-read bytes must equal the labeller's, or the run fails,
    observed (which trace gave each source), beyond_days, downloaded_days, other_days ({source: [days]}, from each present ReadExtent),
    labeller_hash.
`daytruth/2` is `daytruth/1` plus `touched_days`; the measure refuses a `/1` file, as `labeller_hash` does not cover this module and the schema is the guard against output of older code.
`labeller_hash` is the sha256 over the import walk of the labeller, the pipeline's resources and `postrun` (the entries below), in `measure.pin_hash`'s format, computed once
per pass: the measure can refuse day truth made by other code. The job itself never reads or rewrites an existing output (done = the file exists), so a pass from other code
leaves the earlier outputs as they are, and a mixture of hashes is for the measure to refuse.

Incremental: an attempt directory is taken when its `<attempt>.pulled.json` marker sits beside it (`snapshot.fetch`'s: no marker, not whole, not read), its block is one of
`blocks` (main) and its option one of `options`, and it has no output. A run that raises leaves `<attempt>.error.json` ({error: repr cut to 300}), is counted
failed and is not retried in that pass; a later pass retries it only with `--retry-failed`, and counts it failed meanwhile (so a failure never drops out of the line).
A run is counted from the files it left, not from what a worker said. Runs are grouped by instance, a whole group to one forked worker (one reference per instance), as
`postrun._process_all` does; a worker that dies fails every run of its group that has no output. One pass at a time: a lock in DIR refuses a second."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import multiprocessing
import os
import re
import resource
import sys
import threading
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from icsa.instruments import readext as R
from icsa.pipeline.loadrec import resolve_record
from icsa.records import OmissionLabel

SCHEMA = "daytruth/2"
WALK_ENTRIES = ("icsa/instruments/labeller.py", "icsa/pipeline/resources.py", "icsa/pipeline/postrun.py")
OPTIONS = ("T", "T-unpaginated", "D", "M")      # extract's: T and D get the same reader (science, #34 07:01Z); T-unpaginated is in the pagination block only
SOURCES = ("fetched", "delivered", "read")      # the RunLabel's ReadExtents; "analysed" is the fourth
BLOCKS = ("main",)
LOCK = ".daytruth.lock"
_ATTEMPT = re.compile(r"attempt(\d+)\.try(\d+)")
_ERROR_CUT = 300


class Busy(RuntimeError):
    """Another pass holds the output directory's lock."""


# ---- the hash ---------------------------------------------------------------------------------------------------------------------------
def labeller_hash(root: Path | None = None) -> str:
    """sha256 over (relative path, sha256 of content), sorted by path, of every file in the import walk of `WALK_ENTRIES` (`validate.code_files`, which also seeds every
    `icsa/instruments/sim/*.py`), in the format of `measure.pin_hash`. `root`: the repository (default: the one this code was imported from)."""
    from icsa.instruments.validate import REPO, code_files
    root = Path(root or REPO)
    h = hashlib.sha256()
    for rel in sorted(code_files(root, entries=WALK_ENTRIES)):
        h.update(rel.encode() + b"\0" + hashlib.sha256((root / rel).read_bytes()).digest())
    return h.hexdigest()


# ---- per-day coverage -------------------------------------------------------------------------------------------------------------------
def required_cells(required) -> dict[int, int]:
    """Day index -> the number of required cells that day, over baseline and target together; a day with no required cell is not a required day."""
    out: dict[int, int] = {}
    for part in (required.baseline, required.target):
        counts = part.mask.sum(axis=(1, 2))
        for d, n in zip(part.days.tolist(), counts.tolist()):
            if n:
                out[int(d)] = out.get(int(d), 0) + int(n)
    return dict(sorted(out.items()))


def day_coverage(required, extent) -> dict[int, float]:
    """Per required day, the share of that day's required cells `extent` holds (both parts together: a day in both would otherwise be overwritten); only days above 0.
    `extent` is intersected with `required`, so cells beyond it count for nothing. A box that is not the required one is an error, not a guess."""
    num: dict[int, int] = {}
    den = required_cells(required)
    for req, got in ((required.baseline, extent.baseline), (required.target, extent.target)):
        if got.box != req.box:
            raise ValueError(f"extent box {got.box} is not the required box {req.box}")
        at = {int(d): k for k, d in enumerate(got.days.tolist())}
        for k, d in enumerate(req.days.tolist()):
            j = at.get(int(d))
            if j is not None:
                n = int((req.mask[k] & got.mask[j]).sum())
                if n:
                    num[int(d)] = num.get(int(d), 0) + n
    return {d: num[d] / den[d] for d in sorted(num)}


def _by_day(cov: dict[int, float]) -> dict[str, float]:
    return {str(d): f for d, f in cov.items()}


# ---- file-touch evidence ----------------------------------------------------------------------------------------------------------------
LOGS = ("proxy.jsonl", "gate_requests.jsonl", "remote.jsonl", "fuse.jsonl", "localread.jsonl", "strace.txt")       # what `RunLabel.observed` names for fetched and delivered


def touched_days(reads, index, path_map=None) -> list[int]:
    """The days of every file `reads` moved a byte of: a whole-file read, or a range of positive length. A file the index holds gives all the days it holds (S2's one file, all of
    them: its name carries no day); a file it does not hold, the day in its name (S1's). A file of no byte (an empty range) is not touched."""
    pm = path_map or (lambda p: p)
    out: set[int] = set()
    for p in set(reads.ranges) | set(reads.whole_files):
        if not (p in reads.whole_files or any(b > a for a, b in reads.ranges.get(p, ()))):
            continue
        fl = index.get(pm(p))
        if fl is None:
            d = R.day_of_name(pm(p))
            if d is not None:
                out.add(int(d))
        else:
            out.update(int(d) for d in fl.days.tolist())
    return sorted(out)


def _reads_of(name: str, run_dir: Path, option: str, index, local_roots) -> tuple:
    """(ByteReads, path_map) of the log `name`, as `label_run` reads it for the source it filed under that name."""
    from icsa.instruments.crosscheck import file_sizes, gate_reads
    from icsa.instruments.labeller import _download_map
    p = run_dir / name
    if name not in LOGS or not p.is_file():
        raise ValueError(f"the labeller names the log {name!r}, which is not one of {LOGS} or is not in the run directory")
    if name == "proxy.jsonl":
        return R.proxy_reads(R.jsonl(p)), None
    if name == "gate_requests.jsonl":
        return gate_reads(list(R.jsonl(p)), getattr(index, "ids", None), file_sizes(index))[0], None
    if name == "remote.jsonl":
        rem = R.ByteReads()
        for e in R.jsonl(p):
            rem.add(e["path"], e["offset"], e["offset"] + e["size"])
        return rem, None
    if name == "fuse.jsonl":
        return R.fuse_reads(R.jsonl(p)), None
    dmap = _download_map(run_dir / "trace") if option == "D" else {}
    pm = lambda q: dmap.get(q, q)                                  # noqa: E731
    if name == "localread.jsonl":
        return R.fuse_reads(R.jsonl(p)), pm
    return R.strace_reads(p.read_text(errors="replace"), roots=[str(r) for r in local_roots]), pm


def same_extent(a, b) -> bool:
    return all(x.box == y.box and np.array_equal(x.days, y.days) and np.array_equal(x.mask, y.mask) for x, y in ((a.baseline, b.baseline), (a.target, b.target)))


def touch_evidence(lab, run_dir: Path, option: str, index, required, local_roots) -> dict[str, list[int]]:
    """{source: touched days} for the fetched and delivered sources the labeller observed. Each log is re-read with the labeller's own readers, and the extent of what was read must be the
    labeller's (`same_extent`): a re-reading that does not give it, or a source with no log named, is an error and the run gets none of this evidence."""
    out: dict[str, list[int]] = {}
    box, base, tgt = required.baseline.box, required.baseline.days, required.target.days
    for src in ("fetched", "delivered"):
        ro = getattr(lab, src)
        if ro is None:
            continue
        name = lab.observed.get(src)
        reads, pm = _reads_of(str(name), run_dir, option, index, local_roots)
        if not same_extent(R.to_units(reads, index, box, base, tgt, path_map=pm).extent, ro.extent):
            raise ValueError(f"the {src} bytes re-read from {name} are not the extent the labeller took from it")
        out[src] = touched_days(reads, index, pm)
    return out


def contained(run_dir: Path, rel) -> Path:
    """`run_dir / rel` when it stays inside the run directory once symlinks and `..` are resolved; a path that leaves it (absolute, `..`, a symlink) is an error, never read."""
    p = (run_dir / rel).resolve()
    if not p.is_relative_to(run_dir.resolve()):
        raise ValueError(f"{str(rel)[:80]!r} leaves the run directory")
    return p


# ---- one run ----------------------------------------------------------------------------------------------------------------------------
def relabel(run_dir, res, *, label_fn=None, labeller_hash_value: str | None = None) -> dict:
    """One attempt's day truth. `res`: `icsa.pipeline.resources.Resources`. `label_fn`: `label_run` unless a test injects one. `labeller_hash_value`: this pass's
    hash (computed here, slowly, when not given)."""
    from icsa.instruments.labeller import code_cells_of
    from icsa.pipeline.postrun import _has_trace
    run_dir = Path(run_dir)
    if not run_dir.is_dir():
        raise FileNotFoundError(f"run directory missing: {run_dir}")
    if label_fn is None:
        from icsa.instruments.labeller import label_run as label_fn
    m = _ATTEMPT.fullmatch(run_dir.name)
    if m is None:
        raise ValueError(f"not an attempt directory name: {run_dir.name!r}")
    run_name = run_dir.parent.name
    block, key = run_name.split("__", 1)
    entry = {"run_dir": str(run_dir), "key": key, "block": block, "run_key": run_name, "attempt": int(m.group(1))}
    meta = run_dir / "campaign_attempt.json"
    excluded = bool(json.loads(meta.read_text()).get("exclude_from_analysis")) if meta.is_file() else False     # calibration runs are excluded: not a reason to refuse them
    rec, _raw = resolve_record(run_dir, entry, {"exclude_from_analysis": int(excluded)})
    iid, layout, option = rec.run.instance_id, rec.run.layout, rec.run.option
    required = res.required(iid)
    trace = run_dir / "trace"
    lab = None
    touched: dict[str, list[int]] = {}
    if _has_trace(trace):       # as `process_run`: no tracer start, no extent, and the pipeline calls no labeller
        for rel in ("trace", rec.output_dir, *(n for n in LOGS if (run_dir / n).exists() or (run_dir / n).is_symlink())):
            contained(run_dir, rel)             # nothing the labeller reads leaves the run directory: not by the record's paths, not by a link
        cands = [c for c in (run_dir / "cells" / "cells.jsonl", run_dir / rec.code_cells_path) if c.is_file()]
        cells = next(iter(cands), None)
        if cells is not None:
            contained(run_dir, cells.relative_to(run_dir) if cells.is_relative_to(run_dir) else cells)
        code = code_cells_of(cells) if cells else None
        index, local_roots = res.index(layout), res.local_roots(option, run_dir)
        lab = label_fn(option.value, trace, run_dir / rec.output_dir, index, required, platform_dir=run_dir,
                       local_roots=local_roots, dir_sizes=res.dir_sizes(layout), code_text=code)
        touched = touch_evidence(lab, run_dir, option.value, index, required, local_roots)
    coverage: dict[str, dict[str, float]] = {}
    beyond: dict[str, list[int]] = {}
    downloaded: dict[str, list[int]] = {}
    other: dict[str, list[int]] = {}
    if lab is not None:
        for s in SOURCES:
            ro = getattr(lab, s)
            if ro is not None:         # None is "not observed": the key is left out, never an empty coverage
                coverage[s] = _by_day(day_coverage(required, ro.extent))
                beyond[s], downloaded[s], other[s] = ([int(d) for d in x] for x in (ro.beyond_days, ro.downloaded_days, ro.other_days))
        coverage["analysed"] = _by_day(day_coverage(required, lab.analysed))
    return {"schema": SCHEMA, "run_key": run_name, "block": block, "attempt": entry["attempt"], "attempt_dir": run_dir.name,
            "option": option.value, "layout": layout.value, "instance": iid,
            "label": (lab.label if lab is not None else OmissionLabel.UNKNOWN).value, "no_trace": lab is None,
            "required_days": list(required_cells(required)), "coverage": coverage, "touched_days": touched,
            "observed": dict(lab.observed) if lab is not None else {},
            "beyond_days": beyond, "downloaded_days": downloaded, "other_days": other,
            "labeller_hash": labeller_hash_value if labeller_hash_value is not None else labeller_hash()}


# ---- files ------------------------------------------------------------------------------------------------------------------------------
def _private_dir(path: Path) -> None:
    """Created mode 0700 (and set so: mkdir's mode is cut by the umask); a directory that exists is left as it is. A symbolic link is refused, whatever it points at: a result written
    through one would land outside the sealed directory."""
    if path.is_symlink():
        raise ValueError(f"{path} is a symbolic link: nothing is written through one")
    if not path.is_dir():
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(path, 0o700)


def _write_private(path: Path, text: str) -> None:
    """By rename: a reader sees the old file or the whole new one. The temporary has its own name (never `<attempt>.json` or `<attempt>.error.json`) and mode 0600."""
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w") as fh:
            os.fchmod(fh.fileno(), 0o600)
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def out_path(out_dir: Path, attempt_dir: Path) -> Path:
    return Path(out_dir) / attempt_dir.parent.name / f"{attempt_dir.name}.json"


def error_path(out_dir: Path, attempt_dir: Path) -> Path:
    return Path(out_dir) / attempt_dir.parent.name / f"{attempt_dir.name}.error.json"


def _record_error(out_dir: Path, d: Path, err: BaseException | str) -> None:
    _private_dir(out_path(out_dir, d).parent)
    _write_private(error_path(out_dir, d), json.dumps({"error": (err if isinstance(err, str) else repr(err))[:_ERROR_CUT]}))


@contextmanager
def _lock(out_dir: Path):
    fd = os.open(out_dir / LOCK, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        os.fchmod(fd, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            raise Busy(f"another pass holds {out_dir / LOCK}") from e
        yield
    finally:
        os.close(fd)


# ---- which attempts ---------------------------------------------------------------------------------------------------------------------
def attempt_dirs(mirror, *, blocks=BLOCKS, options=OPTIONS, marker: bool = True) -> list[Path]:
    """The attempt directories (`**/runs/<block>__<instance>__<option>__...__s<seed>/attempt<N>.try<M>/`) of these blocks and options, in path order. `marker`: only those with
    `snapshot.fetch`'s `<attempt>.pulled.json` beside them. The walk does not enter a run directory below its attempts (a run's trace is large)."""
    out = []
    for root, dirs, _files in os.walk(mirror):
        here = Path(root)
        parts = here.name.split("__")
        if here.parent.name != "runs" or len(parts) < 6:
            continue
        if parts[0] in blocks and parts[2] in options:
            for a in sorted(dirs):
                d = here / a
                if _ATTEMPT.fullmatch(a) and (not marker or d.with_name(a + ".pulled.json").is_file()):
                    out.append(d)
        dirs[:] = []
    return sorted(out, key=str)


def by_instance(dirs) -> list[list[Path]]:
    """Whole instance groups, in instance order: the cached reference serves a group, and a worker takes one group at a time."""
    groups: dict[str, list[Path]] = {}
    for d in dirs:
        groups.setdefault(d.parent.name.split("__")[1], []).append(d)
    return [groups[k] for k in sorted(groups)]


# ---- the pass ---------------------------------------------------------------------------------------------------------------------------
_SHARED: tuple = ()          # set in each worker (inherited by the fork): the resources, the output directory, the labeller and this pass's hash


def _process_group(group, res, out_dir, label_fn, lhash) -> None:
    """Writes each run's file and returns nothing: no label leaves the worker. A run that raises gets its error file."""
    for d in group:
        try:
            with open(os.devnull, "w") as quiet, contextlib.redirect_stdout(quiet):      # nothing a library prints reaches the line the pass prints
                doc = relabel(d, res, label_fn=label_fn, labeller_hash_value=lhash)
            _private_dir(out_path(out_dir, d).parent)
            _write_private(out_path(out_dir, d), json.dumps(doc))
            error_path(out_dir, d).unlink(missing_ok=True)       # a retry that worked
        except Exception as e:      # noqa: BLE001 -- listed in its error file and counted, never dropped
            _record_error(out_dir, d, e)


def _init_worker(worker_gib: int, shared: tuple) -> None:
    global _SHARED
    resource.setrlimit(resource.RLIMIT_AS, (worker_gib << 30, worker_gib << 30))
    _SHARED = shared


def _work(group) -> None:
    _process_group(group, *_SHARED)


def _run_groups(groups, shared: tuple, workers: int, worker_gib: int) -> None:
    """Serial with one worker; else in forked workers, each under `worker_gib` of address space. A group whose worker died is not reported here: the caller finds its
    runs with no output."""
    if workers <= 1:
        for g in groups:
            try:
                _process_group(g, *shared)
            except Exception:       # noqa: BLE001 -- the caller writes the error file of each run left without a result
                pass
        return
    if threading.active_count() > 1:     # a fork copies a lock another thread holds, locked for good (the netCDF lock, say)
        raise ValueError("--workers needs a single-threaded parent: it forks")
    with ProcessPoolExecutor(workers, mp_context=multiprocessing.get_context("fork"), initializer=_init_worker, initargs=(worker_gib, shared)) as ex:
        futures = []
        for g in groups:
            try:
                futures.append(ex.submit(_work, g))
            except Exception:       # noqa: BLE001 -- a worker already died: the pool takes no more
                pass
        for f in futures:
            try:
                f.result()
            except Exception:       # noqa: BLE001 -- BrokenProcessPool, here and for the groups after it
                pass


def run(mirror, out_dir, res_factory, *, workers: int = 1, done_marker_check: bool = True, blocks=BLOCKS, options=OPTIONS, retry_failed: bool = False,
        label_fn=None, lhash: str | None = None, worker_gib: int = 8) -> dict:
    """One incremental pass; prints one line and returns the same three counts. `res_factory()` builds the resources (`Production`), called once in the parent, which
    preloads them before the fork (and not at all when there is nothing to do). `done_marker_check=False` reads attempts with no marker: tests only."""
    if workers < 1:
        raise ValueError("workers must be at least 1")
    mirror, out_dir = Path(mirror), Path(out_dir)
    lhash = lhash if lhash is not None else labeller_hash()
    _private_dir(out_dir)
    with _lock(out_dir):
        todo: list[Path] = []
        skipped = failed = 0
        by_out: dict[Path, list[Path]] = {}                  # one output per attempt, however many mirror trees hold a copy of it
        for d in attempt_dirs(mirror, blocks=blocks, options=options, marker=done_marker_check):
            by_out.setdefault(out_path(out_dir, d), []).append(d)
        for op in by_out:
            _private_dir(op.parent) if op.parent.is_symlink() else None      # a link in the sealed directory ends the pass before anything is read or written
        for op, copies in by_out.items():
            d = copies[0]
            if op.is_file():
                skipped += 1
            elif len(copies) > 1:                            # which copy is the truth is nobody's to pick: neither is read, and the run is listed as failed
                _record_error(out_dir, d, f"{len(copies)} mirrored copies of one attempt: none is read")
                failed += 1
            elif error_path(out_dir, d).is_file() and not retry_failed:
                failed += 1                                  # an earlier pass's failure, still standing
            else:
                todo.append(d)
        processed = 0
        if todo:
            res = res_factory()
            if workers > 1:
                try:
                    res.preload()        # shared with the workers by the fork, not built once by each
                except Exception:        # noqa: BLE001 -- only a saving: each run then fails on it and is listed, as in serial
                    pass
            _run_groups(by_instance(todo), (res, out_dir, label_fn, lhash), workers, worker_gib)
            for d in todo:               # counted from the files, not from what a worker said
                if out_path(out_dir, d).is_file():
                    processed += 1
                else:
                    if not error_path(out_dir, d).is_file():
                        _record_error(out_dir, d, "no result: the worker ended before this run")
                    failed += 1
    print(f"daytruth: processed {processed}, skipped {skipped} (done), failed {failed}")
    return {"processed": processed, "skipped": skipped, "failed": failed}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="icsa.faults.mainaudit.daytruth", description=__doc__.split("\n\n")[0])
    ap.add_argument("mirror", help="the mirror holding the run directories (`**/runs/<block>__<key>/attempt<N>.try<M>`, each with its .pulled.json)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=1, help="forked workers, one instance group at a time. Never beside a timed run on the run host")
    ap.add_argument("--worker-gib", type=int, default=8, help="each worker's address-space limit")
    ap.add_argument("--blocks", default=",".join(BLOCKS), help="comma-separated; main only by default")
    ap.add_argument("--retry-failed", action="store_true", help="retry the runs that have an error file")
    ap.add_argument("--index-root", default=None, help="as icsa.pipeline: the data root holding the full layout index (default: paths.DATA_ROOT)")
    ap.add_argument("--data-dir", default=None, help="as icsa.pipeline: the S1 copy the reference recomputes from")
    ap.add_argument("--s1-dir", default="s1z", help="as icsa.pipeline: the S1 directory as the agent lists it")
    ap.add_argument("--mount-root", default=None, help="as icsa.pipeline: M, M+: the mount root, for strace-based read evidence")
    a = ap.parse_args(argv)

    def factory():
        from icsa.pipeline.resources import Production      # the labels must be the pipeline's: pass it the options the pipeline's run had
        return Production(Path(a.index_root) if a.index_root else None, a.s1_dir, Path(a.mount_root) if a.mount_root else None,
                          Path(a.data_dir) if a.data_dir else None)
    try:
        run(a.mirror, a.out, factory, workers=a.workers, blocks=tuple(b for b in a.blocks.split(",") if b), retry_failed=a.retry_failed, worker_gib=a.worker_gib)
    except Busy as e:
        print(f"daytruth: {e}", file=sys.stderr)
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
