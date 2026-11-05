"""A numeric check on the coders (#34, science 5 Nov 11:09Z): replay every inspected run's saved mask against two references, with no reader and no LLM.

    python -m snapshot.coderreplay plan    <seal> --answers-root DIR --cache DIR      # host: who is replayed, what is to compute (writes <seal>/coder_replay/work/)
    python -m snapshot.coderreplay compute --jobs F --out DIR --pack-dir DIR           # the detection, on any host that has the tree, numpy, netCDF4 and the data pack (site_a)
    python -m snapshot.coderreplay collect <seal> --cache DIR                          # host: F1 per run, <seal>/coder_replay/coder_replay.csv + meta.json
    python -m snapshot.coderreplay pack    --out DIR                                   # cut the 25 box slices the detection needs out of the campaign's box cache

For every packet of set R or C whose two coders both answered, with `both_agree_exactly` (`decide.decomposition(...)["computable"]`) and a saved mask:

1. the coders' extent: the required (day, sea cell) pairs minus the exact set of pairs the extraction leaves out. That set is rebuilt from the coder's answer with `compare.py`'s own
   helpers and checked against `compare.compare`'s `missing_extent_sha256` (and the decision's); a run whose rebuild differs is NOT replayed (`extent_rebuild_mismatch`);
2. two references through the frozen code only: `scoring.reference._computed_detection` (= `refdet.computed_fields` + `refdet.detect`) on the full required extent (`full`, which must equal the frozen
   truth cell for cell, else the instance is not replayed) and `scoring.reference.counterfactual` on the coders' extent (`cf`);
3. `f1_full` and `f1_extent` = `scoring.masks.cell_day_f1` of the run's mask (`parse_run_output`) against each. Undefined (the reference has no active unit) is an empty cell with a note, never 0.

A complete extraction (nothing missing) needs no second detection: its extent is the full one (tested against a real counterfactual). Detections are cached, not F1 values, keyed by instance,
the extent's digest, the code and the data: an interim computes only the extents it has not seen. The cache and every output are sealed (mode 700/600); nothing prints a per-run value.

Not replayed, with the reason per run: not_in_population, no_run_dir, not_coded, coders_pending, coder_no_valid_answer, extraction_not_exact, extractions_differ, answer_unreadable,
answer_changed_since_decision, extent_rebuild_mismatch, no_run_record, mask_missing, mask_invalid, truth_mismatch, compute_failed:<code>, compute_unavailable, time_box.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import os          # noqa: E402
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")          # a BLAS with one thread per process: a 192-core BLAS raised MemoryError here before

import argparse    # noqa: E402
import base64      # noqa: E402
import csv         # noqa: E402
import functools   # noqa: E402
import hashlib     # noqa: E402
import json        # noqa: E402
import tempfile    # noqa: E402
import time        # noqa: E402
import zlib        # noqa: E402
from concurrent.futures import ProcessPoolExecutor    # noqa: E402
from pathlib import Path    # noqa: E402

import numpy as np   # noqa: E402

from icsa import grid, refdet    # noqa: E402
from icsa.extent import CellBox, Extent, PartedExtent    # noqa: E402
from icsa.inspection import compare as CMP, decide    # noqa: E402
from icsa.instances import load as L    # noqa: E402
from icsa.records import Layout, Option    # noqa: E402,F401
from icsa.scoring import events as E    # noqa: E402
from icsa.scoring import masks as M    # noqa: E402
from icsa.scoring import reference as R    # noqa: E402

FORMAT = "coder-replay/1"
ROOT = Path(__file__).resolve().parents[1]
CODE_FILES = ("icsa/refdet/__init__.py", "icsa/refdet/core.py", "icsa/scoring/reference.py", "icsa/scoring/masks.py", "icsa/scoring/events.py", "icsa/extent.py", "icsa/grid.py",
              "icsa/inspection/compare.py", "icsa/instances/required.py", "icsa/instances/load.py", "snapshot/coderreplay.py")
DEFAULT_BOXSST = Path("/mnt/volume2/icsa-2027/instances/boxsst")
CHUNK = 25          # jobs of one instance that one worker process takes at a time (the instance's reference is built once per chunk)

COLUMNS = ["run_key", "block", "key", "set", "instance_id", "option", "layout", "model", "instrument_label", "label", "coders_pair", "replayed", "f1_full", "f1_extent", "f1_full_note", "f1_extent_note",
           "cf_computation_f1", "cf_omission_f1", "cf_computation_note", "cf_omission_note", "f1_extent_vs_full",
           "coders_coverage_baseline", "coders_coverage_target", "instrument_coverage_baseline", "instrument_coverage_target", "instrument_cf_computation_f1", "instrument_cf_omission_f1",
           "missing_baseline_days", "missing_target_days", "missing_baseline_ranges", "missing_target_ranges", "missing_cell_days_baseline", "missing_cell_days_target",
           "cells_missing_every_day", "why_not_replayed"]


class ReplayError(Exception):
    """A run or an instance that cannot be replayed; `reason` is the code that goes in the table."""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason, self.detail = reason, detail


# ---------------------------------------------------------------------------------------------------------------------------------- identity
@functools.lru_cache(maxsize=1)
def code_sha() -> str:
    """The sha256 of the files the detection and the extent are a function of (frozen code and this file). The host and the worker must agree on it, or a result is refused."""
    h = hashlib.sha256()
    for n in CODE_FILES:
        h.update(n.encode() + b"\0" + (ROOT / n).read_bytes() + b"\0")
    return h.hexdigest()


@functools.lru_cache(maxsize=1)
def data_sha() -> str:
    """The committed instance manifest and sea masks (the manifest also pins the frozen truth's sha256)."""
    h = hashlib.sha256()
    for n in ("instances.json", "sea_masks.npz"):
        h.update((L.DATA / n).read_bytes())
    return h.hexdigest()


def key_sha(code: str | None = None, data: str | None = None) -> str:
    return hashlib.sha256(f"{FORMAT}|{code or code_sha()}|{data or data_sha()}".encode()).hexdigest()[:16]


@functools.lru_cache(maxsize=1)
def _manifest():
    m = L.load_instances()
    return m, {r["instance"]["instance_id"]: r for r in m["instances"]}, L.load_sea_masks(L.DATA / m["sea_masks"]["file"], m["sea_masks"]["sha256"])


# ---------------------------------------------------------------------------------------------------------------------------------- the coders' extent
def missing_grid(ans: dict, req: CMP.Required) -> tuple[np.ndarray, list, np.ndarray]:
    """(missing, day_list, sea_flat): bool (len(day_list), n_sea), True where the extraction leaves a required (day, sea cell) pair out. Rows: the sorted required dates; columns: the sea
    cells in row-major order. This is the construction `compare.compare` makes (same helpers, same order) for an EXACT extraction; its digest is checked against `compare.compare`'s."""
    c, x = ans["cells"], ans["exceptions"]
    if (any(e["status"] == "CANNOT_TELL" for e in ans["baseline"]) or ans["target"]["status"] == "CANNOT_TELL" or c["status"] == "CANNOT_TELL" or x["status"] == "CANNOT_TELL"
            or (c["status"] == "SOME_MISSING" and c["missing_rule"].strip())):
        raise ReplayError("extraction_not_exact")
    day_list = sorted(req.all_days())
    dpos = {d: k for k, d in enumerate(day_list)}
    sea_flat = np.flatnonzero(req.sea.ravel())
    cpos = np.full(req.sea.size, -1)
    cpos[sea_flat] = np.arange(sea_flat.size)
    g = np.zeros((len(day_list), sea_flat.size), dtype=bool)

    def cols(cellmask):
        return cpos[np.flatnonzero(cellmask.ravel())]

    def rows(days):
        return [dpos[d] for d in days if d in dpos]
    by_year = {e["year"]: e for e in ans["baseline"]}
    for y in sorted(req.baseline_days):
        e = by_year.get(y)
        if e is None:
            raise ReplayError("extraction_not_exact", f"no entry for baseline year {y}")
        gap = req.baseline_days[y] - (CMP._days(e["ranges"]) if e["status"] == "RANGES" else set())
        if gap:
            g[rows(gap), :] = True
    t = ans["target"]
    gap = req.target_days - (CMP._days(t["ranges"]) if t["status"] == "RANGES" else set())
    if gap:
        g[rows(gap), :] = True
    if c["status"] == "SOME_MISSING" and c["missing_boxes"]:
        bc = CMP._box_cells(req, c["missing_boxes"])
        if int(bc.sum()):
            g[:, cols(bc)] = True
    if x["status"] == "LISTED":
        all_req = req.all_days()
        for it in x["items"]:
            span = CMP._days(it["ranges"])
            n = it["keep_every_nth_day"]
            if n > 1:
                kept = set()
                for r in it["ranges"]:
                    a, b = CMP.parse_date(r["start"]), CMP.parse_date(r["end"])
                    kept.update(a + CMP.dt.timedelta(s) for s in range(0, (b - a).days + 1, n))
                span = span - kept
            days = (span & all_req) if it["ranges"] else set(all_req)
            cells = req.sea if it["cells"] == "ALL" else CMP._box_cells(req, it["boxes"])
            if days and cells.any():
                g[np.ix_(rows(days), cols(cells))] = True
    return g, day_list, sea_flat


def grid_digest(g: np.ndarray) -> str:
    """`compare.compare`'s `missing_extent_sha256` of a missing grid."""
    return hashlib.sha256(np.packbits(g).tobytes() + str(g.shape).encode()).hexdigest()


def analysed_extent(required: PartedExtent, g: np.ndarray, day_list: list, sea_flat: np.ndarray) -> PartedExtent:
    """The units the coders say were analysed: the required ones minus the missing grid."""
    dpos = {d: k for k, d in enumerate(day_list)}

    def part(p: Extent) -> Extent:
        keep = np.ascontiguousarray(p.mask).copy()
        flat = keep.reshape(keep.shape[0], -1)
        rws = [dpos[grid.day_date(int(d))] for d in p.days]
        flat[:, sea_flat] &= ~g[rws]
        return Extent(p.box, p.days, keep)
    return PartedExtent(part(required.baseline), part(required.target))


def _fmt_ranges(days) -> str:
    return ";".join(f"{a}..{b}" for a, b in CMP._span(days))


def missing_summary(g: np.ndarray, day_list: list, req: CMP.Required) -> dict:
    """What the extraction leaves out, for the table: days with at least one missing sea cell (counts and ranges), missing cell-days by part, and the cells missing on every required day."""
    base = set().union(*req.baseline_days.values())
    rb = [k for k, d in enumerate(day_list) if d in base]
    rt = [k for k, d in enumerate(day_list) if d in req.target_days]
    anyday = g.any(axis=1)
    mb, mt = [day_list[k] for k in rb if anyday[k]], [day_list[k] for k in rt if anyday[k]]
    n_sea = int(req.sea.sum())
    cd_b, cd_t = int(g[rb].sum()), int(g[rt].sum())
    return {"missing_baseline_days": len(mb), "missing_target_days": len(mt), "missing_baseline_ranges": _fmt_ranges(mb), "missing_target_ranges": _fmt_ranges(mt),
            "missing_cell_days_baseline": cd_b, "missing_cell_days_target": cd_t, "cells_missing_every_day": int(g.all(axis=0).sum()) if g.shape[0] else 0,
            # the coders' coverage, the instrument's own definition (1 - missing / required, per part): what coverage.py hands the analysis
            "coders_coverage_baseline": repr(1 - cd_b / (len(rb) * n_sea)), "coders_coverage_target": repr(1 - cd_t / (len(rt) * n_sea))}


def pack_grid(g: np.ndarray) -> dict:
    return {"shape": list(g.shape), "z": base64.b64encode(zlib.compress(np.packbits(g).tobytes(), 6)).decode()}


def unpack_grid(d: dict) -> np.ndarray:
    n = int(np.prod(d["shape"]))
    return np.unpackbits(np.frombuffer(zlib.decompress(base64.b64decode(d["z"])), np.uint8), count=n).reshape(d["shape"]).astype(bool)


# ---------------------------------------------------------------------------------------------------------------------------------- the detection (frozen code)
class BoxCache:
    """The campaign's own box cache (`instances.cache`): box<kk>.npy, shape (days since 1991-12-27, h, w)."""

    def __init__(self, root: Path = DEFAULT_BOXSST):
        self.root = Path(root)

    def load(self, k: int, days: np.ndarray) -> np.ndarray:
        from icsa.instances import cache as C
        mm = np.load(self.root / f"box{k:02d}.npy", mmap_mode="r")
        return np.asarray(mm[np.asarray(days) - C.FIRST_IDX])


class PackDir:
    """The slices of the box cache one machine needs: box<kk>.days.npy (sorted day indices) and box<kk>.sst.npy (the same rows of the box cache)."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def load(self, k: int, days: np.ndarray) -> np.ndarray:
        have = np.load(self.root / f"box{k:02d}.days.npy")
        sst = np.load(self.root / f"box{k:02d}.sst.npy", mmap_mode="r")
        days = np.asarray(days)
        idx = np.searchsorted(have, days)
        if (idx >= have.size).any() or not np.array_equal(have[np.minimum(idx, have.size - 1)], days):
            raise ReplayError("pack_missing_days", f"box {k}")
        return np.asarray(sst[idx])


def build_ref(rec: dict, sea_masks: dict, source) -> R.Reference:
    """The `Reference` of an instance without the published-fields detection and without the frozen truth (both are checked or not needed elsewhere): the same data, extent, sea
    cells and `full` detection `scoring.reference.build_reference` makes. `gt` is `full` here; the caller compares `full` with the frozen truth."""
    i = rec["instance"]
    inst = L.instance(rec)
    box = CellBox(i["lat0"], i["lat1"], i["lon0"], i["lon1"])
    req = L.required_extent(rec, sea_masks[i["region_id"]])
    tdays = R.target_days_of(inst)
    k = int(i["region_id"][1:])
    sst_b, sst_t = source.load(k, req.baseline.days), source.load(k, tdays)
    sea = refdet.sea_cells(sst_b, sst_t)
    if not np.array_equal(sea, sea_masks[i["region_id"]]):
        raise ReplayError("sea_mismatch", i["instance_id"])
    full = R._computed_detection(refdet, box, sea, tdays, req, sst_b, sst_t, req.baseline.mask, req.target.mask)
    return R.Reference(instance=inst, box=box, required=req, target_days=tdays, sea=sea, sst_baseline=sst_b, sst_target=sst_t, gt=full, full=full, refdet=refdet, published=None)


def counterfactual_detection(ref: R.Reference, analysed: PartedExtent):
    """The frozen counterfactual: a `refdet.Detection` on exactly the units of `analysed` (within the required extent)."""
    return R.counterfactual(ref, analysed)


def counterfactual_mask(ref: R.Reference, analysed: PartedExtent) -> np.ndarray:
    return np.asarray(counterfactual_detection(ref, analysed).cell_mask, bool)


def detection_from(mask: np.ndarray, active: np.ndarray, tdays: np.ndarray):
    """A `refdet.Detection` from a cached mask and active days (the events are the maximal runs of active days, as `refdet.detect` makes them)."""
    tdays = np.asarray(tdays, np.int64)
    return refdet.Detection(tdays, np.asarray(mask, bool), np.asarray(active, bool), refdet._events_from_active(tdays, np.asarray(active, bool)))


def pack_mask(m: np.ndarray) -> np.ndarray:
    return np.packbits(np.asarray(m, bool).ravel())


def unpack_mask(bits: np.ndarray, shape) -> np.ndarray:
    return np.unpackbits(bits, count=int(np.prod(shape))).reshape(shape).astype(bool)


# ---------------------------------------------------------------------------------------------------------------------------------- results on disk (the worker writes them, the host caches them)
def write_result(path: Path, mask: np.ndarray, *, code: str, digest: str, active: np.ndarray | None = None) -> None:
    bits = pack_mask(mask)
    act = np.packbits(np.asarray(active, bool)) if active is not None else np.zeros(0, np.uint8)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    with os.fdopen(fd, "wb") as fh:
        np.savez(fh, bits=bits, shape=np.array(mask.shape), act=act, nact=np.array(-1 if active is None else len(active)),
                 sha=np.array(hashlib.sha256(bits.tobytes() + b"|" + act.tobytes()).hexdigest()), code=np.array(code), digest=np.array(digest))
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def read_detection(path: Path, *, code: str, digest: str):
    """(mask, active) of a result file (active None if it holds none), or None when the file is absent, unreadable, from other code, for another digest or fails its own checksum."""
    try:
        with np.load(path) as z:
            bits, shape, act, nact = z["bits"], tuple(int(x) for x in z["shape"]), z["act"], int(z["nact"])
            ok = str(z["code"]) == code and str(z["digest"]) == digest and str(z["sha"]) == hashlib.sha256(bits.tobytes() + b"|" + act.tobytes()).hexdigest()
        if not ok:
            return None
        return unpack_mask(bits, shape), (None if nact < 0 else np.unpackbits(act, count=nact).astype(bool))
    except (OSError, ValueError, KeyError):
        return None


def read_result(path: Path, *, code: str, digest: str) -> np.ndarray | None:
    """The mask in a result file, or None when the file is absent, unreadable, from other code, for another digest or fails its own checksum."""
    r = read_detection(path, code=code, digest=digest)
    return None if r is None else r[0]


class DetCache:
    """Detections by (code+data, instance, digest). `full` is cached only after it equalled the frozen truth."""

    def __init__(self, root: Path, key: str | None = None):
        self.root, self.key = Path(root), key or key_sha()

    def path(self, instance_id: str, digest: str) -> Path:
        return self.root / self.key / instance_id / f"{digest}.npz"

    def get(self, instance_id: str, digest: str) -> np.ndarray | None:
        return read_result(self.path(instance_id, digest), code=code_sha(), digest=digest)

    def get_detection(self, instance_id: str, digest: str):
        return read_detection(self.path(instance_id, digest), code=code_sha(), digest=digest)

    def put(self, instance_id: str, digest: str, mask: np.ndarray, active: np.ndarray | None = None) -> None:
        p = self.path(instance_id, digest)
        for d in (self.root, self.root / self.key, p.parent):
            d.mkdir(mode=0o700, exist_ok=True)
        write_result(p, mask, code=code_sha(), digest=digest, active=active)

    def get_summary(self, instance_id: str, digest: str) -> dict | None:
        """What the table says about an extent (a function of the instance and the digest alone): served in place of reading and rebuilding the coder's answer."""
        try:
            d = json.loads(self.path(instance_id, digest).with_suffix(".summary.json").read_text())
        except (OSError, ValueError):
            return None
        return d if d.get("digest") == digest and d.get("code") == code_sha() else None

    def put_summary(self, instance_id: str, digest: str, none_missing: bool, summary: dict) -> None:
        p = self.path(instance_id, digest).with_suffix(".summary.json")
        for d in (self.root, self.root / self.key, p.parent):
            d.mkdir(mode=0o700, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".tmp-")
        with os.fdopen(fd, "w") as fh:
            json.dump({"digest": digest, "code": code_sha(), "none_missing": none_missing, "summary": summary}, fh, sort_keys=True)
        os.chmod(tmp, 0o600)
        os.replace(tmp, p)


# ---------------------------------------------------------------------------------------------------------------------------------- the worker (any host with the tree, numpy, netCDF4 and the pack)
def _run_chunk(spec: dict) -> dict:
    """One instance, some jobs: builds the reference once, writes `full` and one result per extent. A failure is written as <digest>.err (a reason code, no value)."""
    out = Path(spec["out"]) / spec["instance_id"]
    out.mkdir(parents=True, exist_ok=True)
    counts = {"computed": 0, "skipped": 0, "failed": 0, "time_box": 0}
    code = code_sha()
    jobs = spec["jobs"]

    def fail(digest, e):
        counts["failed"] += 1
        (out / f"{digest}.err").write_text(json.dumps({"reason": getattr(e, "reason", type(e).__name__), "detail": getattr(e, "detail", "")[:200] if isinstance(e, ReplayError) else ""}))
    try:
        m, recs, masks = _manifest()
        source = PackDir(spec["pack"]) if spec.get("pack") else BoxCache(spec.get("boxsst") or DEFAULT_BOXSST)
        todo = [j for j in jobs if not (out / f"{j['digest']}.npz").exists()]
        counts["skipped"] = len(jobs) - len(todo)
        if not todo:
            return counts
        ref = build_ref(recs[spec["instance_id"]], masks, source)
    except Exception as e:      # noqa: BLE001 - one instance's failure never stops the others
        for j in jobs:
            fail(j["digest"], e)
        return counts
    req = CMP.Required.from_extent(ref.required)
    for j in todo:
        if spec.get("deadline") and time.time() > spec["deadline"]:
            counts["time_box"] += 1
            continue
        try:
            if j["digest"] == "full":
                write_result(out / "full.npz", ref.full.cell_mask, code=code, digest="full", active=ref.full.active)
            else:
                g = unpack_grid(j["grid"])
                if grid_digest(g) != j["digest"]:
                    raise ReplayError("grid_digest_mismatch")
                day_list = sorted(req.all_days())
                sea_flat = np.flatnonzero(req.sea.ravel())
                if g.shape != (len(day_list), sea_flat.size):
                    raise ReplayError("grid_shape")
                det = counterfactual_detection(ref, analysed_extent(ref.required, g, day_list, sea_flat))
                write_result(out / f"{j['digest']}.npz", det.cell_mask, code=code, digest=j["digest"], active=det.active)
            counts["computed"] += 1
        except Exception as e:      # noqa: BLE001
            fail(j["digest"], e)
    return counts


def compute(jobs_path: Path, out: Path, *, pack_dir: Path | None, boxsst: Path | None = None, procs: int = 1, deadline: float | None = None) -> dict:
    """jobs.jsonl: {"instance_id", "digest" ("full" or a missing-grid digest), "grid" (pack_grid) for an extent}. Only the jobs given are written (the reference of an instance is built once per chunk)."""
    by: dict[str, dict[str, dict]] = {}
    for line in Path(jobs_path).read_text().splitlines():
        if line.strip():
            j = json.loads(line)
            by.setdefault(j["instance_id"], {})[j["digest"]] = j
    chunks = []
    for iid in sorted(by):
        jobs = sorted(by[iid].values(), key=lambda j: (j["digest"] != "full", j["digest"]))          # `full` first when asked for
        for a in range(0, len(jobs), CHUNK):
            part = jobs[a:a + CHUNK]            # each chunk's worker builds the instance's reference once
            chunks.append({"instance_id": iid, "jobs": part, "out": str(out), "pack": str(pack_dir) if pack_dir else None, "boxsst": str(boxsst) if boxsst else None, "deadline": deadline})
    Path(out).mkdir(mode=0o700, parents=True, exist_ok=True)
    tot = {"computed": 0, "skipped": 0, "failed": 0, "time_box": 0, "chunks": len(chunks)}
    t0 = time.time()
    if procs > 1 and len(chunks) > 1:
        with ProcessPoolExecutor(procs) as ex:
            res = list(ex.map(_run_chunk, chunks))
    else:
        res = [_run_chunk(c) for c in chunks]
    for r in res:
        for k in ("computed", "skipped", "failed", "time_box"):
            tot[k] += r[k]
    tot["seconds"] = round(time.time() - t0, 1)
    return tot


# ---------------------------------------------------------------------------------------------------------------------------------- the host: who is replayed
def _population(seal: Path) -> dict:
    rows = {}
    for line in (seal / "inspection" / "population.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r["run_key"]] = r
    return rows


WHY = {"a coder gave no valid answer": "coder_no_valid_answer", "an extraction leaves a part CANNOT TELL or names cells by a rule": "extraction_not_exact",
       "the extractions differ": "extractions_differ"}


def read_final(answers_root: Path, pid: str, coder: str) -> dict | None:
    p = Path(answers_root) / "answers" / pid / coder / "final.json"
    try:
        d = json.loads(p.read_text())
    except (OSError, ValueError):
        return None
    return d if isinstance(d, dict) and d.get("status") == "valid" and isinstance(d.get("answer"), dict) else None


def read_mask(run_dir: str, box, tdays) -> tuple[np.ndarray | None, str]:
    """(mask, "") or (None, reason): the run's saved mask through the frozen mask parser (`parse_run_output` calls it for the mask; the report is not needed here)."""
    from icsa.scoring.report import InvalidOutput, _parse_mask_alias
    rd = Path(run_dir)
    if not rd.is_dir():
        return None, "no_run_dir"
    out_dir = None
    for n in ("run_record.json", "run.json"):
        try:
            out_dir = json.loads((rd / n).read_text())["output_dir"]
            break
        except (OSError, ValueError, KeyError):
            continue
    if out_dir is None:
        return None, "no_run_record"
    try:
        return _parse_mask_alias(rd / out_dir / "mhw_mask.nc", box, tdays)[0], ""
    except InvalidOutput as e:
        return None, e.reason or "mask_invalid"


class Extents:
    """Required extents and `compare.Required`s by instance, built when first asked for."""

    def __init__(self, recs: dict, masks: dict):
        self.recs, self.masks, self._e, self._r = recs, masks, {}, {}

    def extent(self, iid: str) -> PartedExtent:
        if iid not in self._e:
            self._e[iid] = L.required_extent(self.recs[iid], self.masks[self.recs[iid]["instance"]["region_id"]])
        return self._e[iid]

    def required(self, iid: str) -> CMP.Required:
        if iid not in self._r:
            self._r[iid] = CMP.Required.from_extent(self.extent(iid))
        return self._r[iid]


def plan_items(decisions: dict, population: dict, answers_root: Path, ext: Extents, cache: "DetCache | None" = None) -> tuple[list[dict], dict]:
    """(items, grids): one item per packet of set R or C, replayable or with its reason; grids[(instance, digest)] = the packed missing grid of each distinct extent.
    With a cache, an extent whose detection and summary are already in it (checked when they were made) is served by the decision's own `missing_extent_sha256`: the answer is not read again."""
    items, grids = [], {}
    for pid in sorted(decisions["packets"]):
        p = decisions["packets"][pid]
        if p.get("set") not in ("R", "C"):
            continue
        row = population.get(p["run_key"])
        it = {"pid": pid, "run_key": p["run_key"], "set": p["set"], "instance_id": p.get("instance_id"), "option": p.get("option"), "layout": p.get("layout"), "model": p.get("model"),
              "block": (row or {}).get("block"), "key": (row or {}).get("key"), "run_dir": (row or {}).get("run_dir") or "", "why": "",
              # carried through from the decision so the table is self-contained: the instrument's label, the label after the coders, and the coders' agreed verdict (COMPLETE, OMITTING or none)
              "instrument_label": p.get("instrument"), "label": (p.get("decision") or {}).get("label"), "coders_pair": (p.get("decision") or {}).get("pair")}
        items.append(it)
        if row is None:
            it["why"] = "not_in_population"
        elif not it["run_dir"]:
            it["why"] = "no_run_dir"
        elif p.get("not_coded"):
            it["why"] = "not_coded"
        elif p.get("pending") or not p.get("pair"):
            it["why"] = "coders_pending"
        else:
            d1, d2 = (p["coders"][c].get("detail") for c in p["pair"])
            dec = decide.decomposition(d1, d2)
            if not dec["computable"]:
                it["why"] = WHY.get(dec["why"], "extraction_not_exact")
        if it["why"]:
            continue
        try:
            digest0 = d1.get("missing_extent_sha256")
            hit = cache.get_summary(it["instance_id"], digest0) if cache and digest0 else None
            if hit and (hit["none_missing"] or cache.get(it["instance_id"], digest0) is not None):
                it.update(ext_digest="full" if hit["none_missing"] else digest0, **hit["summary"])
                continue
            coder = p["pair"][0]
            fin = read_final(answers_root, pid, coder)
            if fin is None:
                raise ReplayError("answer_unreadable")
            req = ext.required(it["instance_id"])
            v = CMP.compare(fin["answer"], req)
            if v.extraction_sha256 != d1["extraction_sha256"] or v.missing_extent_sha256 != d1["missing_extent_sha256"]:
                raise ReplayError("answer_changed_since_decision")
            g, day_list, sea_flat = missing_grid(fin["answer"], req)
            digest = grid_digest(g)
            if digest != v.missing_extent_sha256:
                raise ReplayError("extent_rebuild_mismatch")
            summ = missing_summary(g, day_list, req)
            it.update(ext_digest=digest, **summ)
            if g.any():
                grids.setdefault((it["instance_id"], digest), pack_grid(g))
            else:
                it["ext_digest"] = "full"
            if cache:
                cache.put_summary(it["instance_id"], digest, not g.any(), summ)
        except ReplayError as e:
            it["why"] = e.reason
        except Exception as e:      # noqa: BLE001 - a malformed answer or a failing comparison is a reason, never a crash
            it["why"] = "answer_unreadable" if isinstance(e, (KeyError, TypeError, ValueError)) else f"plan_failed:{type(e).__name__}"
    return items, grids


def jobs_needed(items: list[dict], grids: dict, cache: DetCache) -> list[dict]:
    """The jobs the cache cannot serve: `full` of each instance with a replayable run, and each distinct extent."""
    out, instances = [], sorted({it["instance_id"] for it in items if not it["why"]})
    for iid in instances:
        if cache.get(iid, "full") is None:
            out.append({"instance_id": iid, "digest": "full"})
    for (iid, digest), packed in sorted(grids.items()):
        if cache.get(iid, digest) is None:
            out.append({"instance_id": iid, "digest": digest, "grid": packed})
    return out


def import_results(staging: Path, cache: DetCache, truth_loader, recs: dict) -> dict:
    """Moves what a worker wrote into the cache, refusing anything from other code, with a bad checksum, or (for `full`) different from the frozen truth. Returns counts and the
    errors by (instance, digest): reason."""
    got = {"imported": 0, "refused": 0}
    errors: dict = {}
    code = code_sha()
    if not Path(staging).is_dir():          # nothing was computed (no job was needed, or no host answered)
        return {**got, "errors": errors}
    for idir in sorted(p for p in Path(staging).iterdir() if p.is_dir() and not p.name.startswith(".")):
        iid = idir.name
        for f in sorted(idir.glob("*.npz")):
            digest = f.stem
            res = read_detection(f, code=code, digest=digest)
            if res is None or res[1] is None:
                got["refused"] += 1
                errors[(iid, digest)] = "result_refused"
                continue
            mask, active = res
            if digest == "full":
                try:
                    if not np.array_equal(mask, truth_loader(recs[iid])):
                        got["refused"] += 1
                        errors[(iid, "full")] = "truth_mismatch"
                        continue
                except Exception:      # noqa: BLE001
                    got["refused"] += 1
                    errors[(iid, "full")] = "truth_unavailable"
                    continue
            cache.put(iid, digest, mask, active)
            got["imported"] += 1
        for f in sorted(idir.glob("*.err")):
            try:
                errors.setdefault((iid, f.stem), json.loads(f.read_text()).get("reason", "failed"))
            except (OSError, ValueError):
                errors.setdefault((iid, f.stem), "failed")
    return {**got, "errors": errors}


def default_truth(rec: dict) -> np.ndarray:
    from icsa.harness.oracle_real import load_truth
    return load_truth(rec).cell_mask


# ---------------------------------------------------------------------------------------------------------------------------------- the host: the table
def f1_pair(agent: np.ndarray, full: np.ndarray, cf: np.ndarray, sea: np.ndarray) -> dict:
    out = {}
    for name, ref in (("full", full), ("extent", cf)):
        v = M.cell_day_f1(agent, ref, sea)
        out[f"f1_{name}"], out[f"f1_{name}_note"] = ("", "reference_has_no_active_unit") if v is None else (repr(float(v)), "")
    return out


def registered_pair(agent: np.ndarray, cf, full, sea: np.ndarray) -> dict:
    """The registered discrepancies with their registered definitions (`scoring.scorer.score_run`): `cf_computation_f1` = the agent's events against the reference's on the extent
    (`events.match_events(agent, cf).f1`), `cf_omission_f1` = that reference's events against the full one's; each undefined (empty, with a note) when its reference has no event. Also the
    cell-day F1 of the extent's reference against the full one."""
    mask = np.asarray(agent, bool) & sea
    agent_ev = [E.event_units(mask, i0, i1) for i0, i1 in E.active_runs(M.day_active(mask))]
    cf_ev, full_ev = R.detection_events(cf, cf.days), R.detection_events(full, full.days)
    comp, omi = E.match_events(agent_ev, cf_ev).f1, E.match_events(cf_ev, full_ev).f1
    cd = M.cell_day_f1(cf.cell_mask, full.cell_mask, sea)
    return {"cf_computation_f1": "" if comp is None else repr(float(comp)), "cf_computation_note": "extent_reference_has_no_event" if comp is None else "",
            "cf_omission_f1": "" if omi is None else repr(float(omi)), "cf_omission_note": "full_reference_has_no_event" if omi is None else "",
            "f1_extent_vs_full": "" if cd is None else repr(float(cd))}


def _mask_task(a):
    return read_mask(*a)


def build_rows(items: list[dict], cache: DetCache, ext: Extents, errors: dict, *, unreached=frozenset(), jobs: int = 1) -> list[dict]:
    """One row per item. The saved masks are parsed in `jobs` processes (streamed, so memory stays flat); F1 and the rows are made here, in item order."""
    todo = [it for it in items if not it["why"]]
    args = []
    for it in todo:
        iid = it["instance_id"]
        args.append((it["run_dir"], ext.extent(iid).baseline.box, R.target_days_of(L.instance(_manifest()[1][iid]))))
    pool = ProcessPoolExecutor(jobs) if jobs > 1 and len(todo) > 8 else None
    masks_iter = iter(pool.map(_mask_task, args, chunksize=8)) if pool else map(_mask_task, args)
    try:
        return _rows(items, cache, ext, errors, unreached, masks_iter)
    finally:
        if pool:
            pool.shutdown(wait=True, cancel_futures=True)


def _rows(items, cache, ext, errors, unreached, masks_iter) -> list[dict]:
    rows = []
    for it in items:
        row = {c: it.get(c, "") for c in COLUMNS}
        row.update(replayed="false", f1_full="", f1_extent="", f1_full_note="", f1_extent_note="", why_not_replayed=it["why"])
        rows.append(row)
        if it["why"]:
            continue
        iid, digest = it["instance_id"], it["ext_digest"]
        agent, why = next(masks_iter)
        try:
            rec = _manifest()[1][iid]
            if agent is None:
                row["why_not_replayed"] = why
                continue
            full_d = cache.get_detection(iid, "full")
            cf_d = full_d if digest == "full" else cache.get_detection(iid, digest)
            full, cf = (None if full_d is None else full_d[0]), (None if cf_d is None else cf_d[0])
            if full is None or cf is None or full_d[1] is None or cf_d[1] is None:
                k = (iid, "full") if full is None else (iid, digest)
                bad = errors.get(k)
                row["why_not_replayed"] = "truth_mismatch" if bad == "truth_mismatch" else f"compute_failed:{bad}" if bad else "time_box" if k in unreached else "compute_unavailable"
                continue
            sea = ext.masks[rec["instance"]["region_id"]]
            row.update(f1_pair(agent, full, cf, sea))
            tdays = R.target_days_of(L.instance(rec))
            row.update(registered_pair(agent, detection_from(cf, cf_d[1], tdays), detection_from(full, full_d[1], tdays), sea))
            row["replayed"] = "true"
        except ReplayError as e:
            row["why_not_replayed"] = e.reason
    return rows


def write_table(path: Path, rows: list[dict], header: str | None = None) -> None:
    """The table, atomically. `header` is the first line (`# snapshot final=<true|false> t=<t>`, as the snapshot's own tables have it: read with skiprows=1)."""
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    with os.fdopen(fd, "w", newline="") as fh:
        if header:
            fh.write(header + "\n")
        w = csv.DictWriter(fh, COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


DEGRADED = ("compute_unavailable", "time_box", "compute_failed", "truth_mismatch")      # a run that could be replayed but the computation did not deliver


def totals(rows: list[dict]) -> dict:
    why: dict[str, int] = {}
    for r in rows:
        if r["why_not_replayed"]:
            why[r["why_not_replayed"].split(":")[0]] = why.get(r["why_not_replayed"].split(":")[0], 0) + 1
    return {"rows": len(rows), "replayed": sum(r["replayed"] == "true" for r in rows), "not_replayed": sum(r["replayed"] != "true" for r in rows), "not_replayed_by_reason": dict(sorted(why.items())),
            "degraded": sum(why.get(k, 0) for k in DEGRADED)}


def instrument_values(seal: Path) -> dict:
    """(block, run key) -> the instrument's own coverage and cf fields as the pipeline scored them (first analysis, no coding), for the runs the INSTRUMENT labelled complete or omitting. The
    pipeline keeps no extents, only these numbers. Empty when the seal has no scored rows."""
    p = Path(seal) / "out" / "pipeline" / "scored_rows.jsonl"
    if not p.is_file():
        return {}
    from icsa.analysis.adapter import load_jsonl
    from icsa.records import OmissionLabel

    def f(v):
        return "" if v is None else repr(float(v))
    return {(r.block, r.run.key()): {"instrument_coverage_baseline": f(r.coverage_baseline), "instrument_coverage_target": f(r.coverage_target),
                                     "instrument_cf_computation_f1": f(r.cf_computation_f1), "instrument_cf_omission_f1": f(r.cf_omission_f1)}
            for r in load_jsonl(p) if r.label in (OmissionLabel.COMPLETE, OmissionLabel.OMITTING)}


def snapshot_final(seal: Path) -> str:
    """'true' or 'false' from the snapshot's own SNAPSHOT.json (the coded analysis if it exists), else 'unknown'."""
    for d in ("out-coded", "out"):
        try:
            return str(bool(json.loads((Path(seal) / d / "SNAPSHOT.json").read_text())["final"])).lower()
        except (OSError, ValueError, KeyError):
            continue
    return "unknown"


def collect(seal: Path, cache_dir: Path, results: Path | None, t: str, jobs: int = 1) -> dict:
    """The table and meta.json from the plan's items, the cache and what the workers brought back. Returns the meta (counts only)."""
    seal, work = Path(seal), Path(seal) / "coder_replay" / "work"
    t0 = time.time()
    m, recs, masks = _manifest()
    ext, cache = Extents(recs, masks), DetCache(cache_dir)
    items = [json.loads(x) for x in (work / "items.jsonl").read_text().splitlines() if x.strip()]
    inst = instrument_values(seal)
    for it in items:
        it.update(inst.get((it.get("block"), it.get("key")), {}))
    errors, unreached = {}, set()
    if results:
        errors = import_results(Path(results), cache, default_truth, recs)["errors"]
        try:
            rem = json.loads((work / "remote.json").read_text())
        except (OSError, ValueError):
            rem = {}
        if rem.get("time_box"):
            asked = [json.loads(x) for x in (work / "jobs.jsonl").read_text().splitlines() if x.strip()]
            done = {(q.parent.name, q.stem) for q in Path(results).glob("*/*") if q.suffix in (".npz", ".err")} if Path(results).is_dir() else set()
            unreached = {(j["instance_id"], j["digest"]) for j in asked} - done
    rows = build_rows(items, cache, ext, errors, unreached=unreached, jobs=jobs)
    final = snapshot_final(seal)
    write_table(seal / "coder_replay" / "coder_replay.csv", rows, f"# snapshot final={final} t={t}")
    meta = {**totals(rows), "t": t, "final": final, "seconds": round(time.time() - t0, 1), "code_sha": code_sha()[:16], "data_sha": data_sha()[:16], "format": FORMAT}
    (seal / "coder_replay" / "meta.json").write_text(json.dumps(meta, indent=1, sort_keys=True))
    os.chmod(seal / "coder_replay" / "meta.json", 0o600)
    return meta


# ---------------------------------------------------------------------------------------------------------------------------------- the pack
def build_pack(out: Path, boxsst: Path = DEFAULT_BOXSST) -> dict:
    """box<kk>.days.npy and box<kk>.sst.npy for the days the 50 instances need (their required baseline and target days, per region), cut from the campaign's box cache; MANIFEST.json."""
    m, recs, masks = _manifest()
    src = BoxCache(boxsst)
    need: dict[int, set] = {}
    for rec in recs.values():
        i = rec["instance"]
        req = L.required_extent(rec, masks[i["region_id"]])
        need.setdefault(int(i["region_id"][1:]), set()).update(map(int, req.baseline.days), map(int, R.target_days_of(L.instance(rec))))
    out = Path(out)
    out.mkdir(mode=0o700, parents=True, exist_ok=True)
    man = {}
    for k, days in sorted(need.items()):
        d = np.array(sorted(days), np.int64)
        np.save(out / f"box{k:02d}.days.npy", d)
        np.save(out / f"box{k:02d}.sst.npy", src.load(k, d))
        man[f"box{k:02d}"] = {n: hashlib.sha256((out / f"box{k:02d}.{n}.npy").read_bytes()).hexdigest() for n in ("days", "sst")}
    (out / "MANIFEST.json").write_text(json.dumps({"format": FORMAT, "files": man}, indent=1, sort_keys=True))
    (out / "SHA256SUMS").write_text("".join(f"{v[n]}  box{k[3:]}.{n}.npy\n" for k, v in sorted(man.items()) for n in ("days", "sst")))
    return {"boxes": len(need), "bytes": sum(p.stat().st_size for p in out.glob("*.npy"))}


# ---------------------------------------------------------------------------------------------------------------------------------- CLI
def _plan_cmd(a) -> int:
    seal = Path(a.seal)
    work = seal / "coder_replay" / "work"
    os.umask(0o077)
    work.mkdir(mode=0o700, parents=True, exist_ok=True)
    m, recs, masks = _manifest()
    ext = Extents(recs, masks)
    decisions = json.loads((seal / "inspection" / "decisions.json").read_text())
    dc = DetCache(a.cache)
    items, grids = plan_items(decisions, _population(seal), Path(a.answers_root), ext, dc)
    jobs = jobs_needed(items, grids, dc)
    (work / "items.jsonl").write_text("".join(json.dumps(it, sort_keys=True) + "\n" for it in items))
    (work / "jobs.jsonl").write_text("".join(json.dumps(j, sort_keys=True) + "\n" for j in jobs))
    print(json.dumps({"items": len(items), "replayable": sum(not it["why"] for it in items), "jobs": len(jobs), "distinct_extents": len(grids)}, sort_keys=True))
    return 0


def _collect_cmd(a) -> int:
    os.umask(0o077)
    meta = collect(Path(a.seal), Path(a.cache), Path(a.results) if a.results else None, a.t, jobs=a.jobs)
    print(json.dumps(meta, sort_keys=True))
    return 10 if meta["degraded"] else 0          # 10: the table exists, but some runs that could be replayed were not (compute unavailable, time box, failure)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m snapshot.coderreplay", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("seal")
    p.add_argument("--answers-root", required=True, help="the coders' sealed directory (answers/<pid>/<coder>/final.json)")
    p.add_argument("--cache", required=True)
    c = sub.add_parser("compute")
    c.add_argument("--jobs", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--pack-dir")
    c.add_argument("--boxsst")
    c.add_argument("--procs", type=int, default=1)
    c.add_argument("--deadline", type=float, help="epoch seconds: jobs not started by then are left (time_box)")
    k = sub.add_parser("collect")
    k.add_argument("seal")
    k.add_argument("--cache", required=True)
    k.add_argument("--results", help="a directory of worker results (<instance>/<digest>.npz) to import first")
    k.add_argument("--t", default="unknown", help="the snapshot's t, for the table's first line and meta.json")
    k.add_argument("--jobs", type=int, default=int(os.environ.get("REPLAY_MASK_JOBS", "4")), help="processes that parse the saved masks")
    b = sub.add_parser("pack")
    b.add_argument("--out", required=True)
    b.add_argument("--boxsst", default=str(DEFAULT_BOXSST))
    a = ap.parse_args(argv)
    try:
        if a.cmd == "plan":
            return _plan_cmd(a)
        if a.cmd == "collect":
            return _collect_cmd(a)
        if a.cmd == "compute":
            os.umask(0o077)
            r = compute(Path(a.jobs), Path(a.out), pack_dir=Path(a.pack_dir) if a.pack_dir else None, boxsst=Path(a.boxsst) if a.boxsst else None, procs=a.procs, deadline=a.deadline)
            print(json.dumps(r, sort_keys=True))
            return 0 if not r["failed"] else 3
        if a.cmd == "pack":
            os.umask(0o077)
            print(json.dumps(build_pack(Path(a.out), Path(a.boxsst)), sort_keys=True))
            return 0
    except (OSError, ValueError, KeyError, ReplayError) as e:
        print(f"coderreplay refused: {type(e).__name__}: {getattr(e, 'reason', '') or str(e)[:120]}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
