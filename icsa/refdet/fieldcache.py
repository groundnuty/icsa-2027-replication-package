"""Precomputed full-domain threshold and climatology fields (computed mode, whole grid).

Ground truth is the computed mode on the S1 values the agents read. Computing the fields per
instance would read the 4,028 baseline daily S1 files every time, so they are computed once
here, band by band, and cut to each instance's box by `load`.

Layout of a cache directory: `m90.npy` and `mclim.npy` (float64, (366, nlat, nlon), written
through memmaps so the domain is never held in memory), `finite_baseline.npy` and `fields.json`,
whose `complete: true` is written only after the last band.

`fields.json` records what the cache was built from: the format, the baseline and the padded day
extent, the estimator, the precision, the sea rule, the source and a fingerprint of the source
files. `check_ground_truth` refuses any cache whose record differs from the frozen method, so a
cache built on another baseline or from changed S1 files can never serve as ground truth.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
from typing import Callable

import numpy as np

from .. import grid, paths
from ..extent import CellBox
from . import Fields, baseline_days, computed_fields, load_sst
from .data import s1_file, s1_index

MAX_WORKERS = 4
META = "fields.json"
PAD = 5
FORMAT = 2
ESTIMATOR = "hazen (MATLAB quantile)"
PRECISION = "float64"
SEA_RULE = "finite on every day of the padded baseline extent (finite_baseline.npy)"
S1_SOURCE = "s1"


def s1_fingerprint(days: np.ndarray, s1_dir=None) -> str:
    """sha256 over (file name, size, mtime) of the S1 daily files of `days`, resolved exactly as the
    reader resolves them (`data.s1_index`): changes whenever any of those files is rebuilt or replaced.
    A missing day raises FileNotFoundError, two files for one date ValueError."""
    s1_dir = Path(s1_dir or paths.S1_DIR)
    index = s1_index(s1_dir)
    h = hashlib.sha256(str(s1_dir.resolve()).encode())
    for d in np.asarray(days, np.int64):
        f = s1_file(index, d)
        st = f.stat()
        h.update(f"\n{f.name} {st.st_size} {st.st_mtime_ns}".encode())
    return h.hexdigest()


def _default_loader(box: CellBox, days: np.ndarray) -> np.ndarray:
    return load_sst(box, days, "s1")


def _band(args):
    lat0, lat1, nlon, days, baseline, loader = args
    loader = loader or _default_loader
    box = CellBox(lat0, lat1, 0, nlon)
    sst = loader(box, days)
    f = computed_fields(sst, days, box, baseline=baseline)
    return lat0, lat1, f.m90, f.mclim, np.isfinite(sst).all(axis=0)


def build(out_dir, *, loader: Callable | None = None, rows_per_band: int = 16, workers: int = 1,
          baseline: tuple[int, int] | None = None, source_label: str | None = None,
          source_fingerprint: str | None = None,
          nlat: int = grid.NLAT, nlon: int = grid.NLON) -> Path:
    """Compute the fields for every band of `rows_per_band` latitude rows and write the cache.

    `loader(box, days)` returns float32 SST (len(days), h, w); the default reads S1 and records
    source "s1" with `s1_fingerprint` of the days read. With another loader, `source_label`
    (default "custom") and an optional `source_fingerprint` are recorded as given.
    With workers > 1 (at most 4) each worker returns one band and the parent writes it.
    """
    if rows_per_band < 1 or not 1 <= workers <= MAX_WORKERS:
        raise ValueError(f"rows_per_band >= 1 and 1 <= workers <= {MAX_WORKERS} required")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    meta_path = out / META
    if meta_path.exists():
        meta_path.unlink()          # an interrupted rebuild must not look complete
    b0, b1 = baseline or baseline_days()
    days = np.arange(b0 - PAD, b1 + PAD + 1, dtype=np.int64)
    if loader is None:
        source_label = S1_SOURCE
        source_fingerprint = s1_fingerprint(days)
    else:
        source_label = source_label or "custom"
    shape = (366, nlat, nlon)
    mm = {name: np.lib.format.open_memmap(out / f"{name}.npy", mode="w+", dtype=np.float64, shape=shape)
          for name in ("m90", "mclim")}
    # cells finite on every day of the required baseline extent (the first half of the sea-cell rule)
    mm["finite_baseline"] = np.lib.format.open_memmap(out / "finite_baseline.npy", mode="w+", dtype=bool,
                                                      shape=(nlat, nlon))
    jobs = [(r, min(r + rows_per_band, nlat), nlon, days, (b0, b1), loader) for r in range(0, nlat, rows_per_band)]
    if workers == 1:
        results = map(_band, jobs)
        pool = None
    else:
        pool = mp.get_context("fork").Pool(workers)
        results = pool.imap(_band, jobs)
    try:
        for lat0, lat1, m90, mclim, fin in results:
            mm["m90"][:, lat0:lat1] = m90
            mm["mclim"][:, lat0:lat1] = mclim
            mm["finite_baseline"][lat0:lat1] = fin
    finally:
        if pool is not None:
            pool.close()
            pool.join()
    for m in mm.values():
        m.flush()
    del mm
    meta = {
        "baseline": [int(b0), int(b1)],
        "days": [int(days[0]), int(days[-1])],
        "format": FORMAT,
        "rows_per_band": rows_per_band,
        "source": source_label,
        "source_fingerprint": source_fingerprint,
        "precision": PRECISION,
        "estimator": ESTIMATOR,
        "sea_rule": SEA_RULE,
        "shape": list(shape),
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "complete": True,
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    return out


def _check(cache: Path) -> None:
    try:
        meta = json.loads((cache / META).read_text())
    except FileNotFoundError:
        raise FileNotFoundError(f"{cache / META} missing: field cache not built") from None
    if not meta.get("complete"):
        raise FileNotFoundError(f"field cache {cache} is not complete")


def check_ground_truth(cache_dir, *, source: str | None = S1_SOURCE, source_fingerprint: str | None = None,
                       nlat: int | None = None, nlon: int | None = None) -> dict:
    """Refuse a cache that cannot serve as ground truth: incomplete, an older format, another
    baseline or padded extent, another estimator, precision or sea rule, another grid, or (when
    given) another source or source fingerprint. Raises ValueError listing every mismatch;
    returns the record when all match. Never falls back."""
    cache = Path(cache_dir)
    _check(cache)
    meta = json.loads((cache / META).read_text())
    nlat = grid.NLAT if nlat is None else nlat     # read at call time: the product grid unless told otherwise
    nlon = grid.NLON if nlon is None else nlon
    b0, b1 = baseline_days()
    want = {"format": FORMAT, "baseline": [int(b0), int(b1)], "days": [int(b0 - PAD), int(b1 + PAD)],
            "estimator": ESTIMATOR, "precision": PRECISION, "sea_rule": SEA_RULE, "shape": [366, nlat, nlon]}
    if source is not None:
        want["source"] = source
    if source_fingerprint is not None:
        want["source_fingerprint"] = source_fingerprint
    bad = [f"{k}: cache has {meta.get(k)!r}, ground truth needs {v!r}" for k, v in want.items() if meta.get(k) != v]
    if bad:
        raise ValueError(f"field cache {cache} cannot serve as ground truth: " + "; ".join(bad))
    return meta


def load(box: CellBox, cache_dir) -> Fields:
    """Fields cut to `box` (copies of the memmap slices). Raises FileNotFoundError unless the cache is complete."""
    cache = Path(cache_dir)
    _check(cache)
    sl = (slice(None), slice(box.lat0, box.lat1), slice(box.lon0, box.lon1))
    m90 = np.load(cache / "m90.npy", mmap_mode="r")
    mclim = np.load(cache / "mclim.npy", mmap_mode="r")
    return Fields(np.array(m90[sl]), np.array(mclim[sl]))


def load_finite_baseline(box: CellBox, cache_dir) -> np.ndarray:
    """bool (h, w): cells whose SST is finite on every day of the required baseline extent."""
    cache = Path(cache_dir)
    _check(cache)
    return np.array(np.load(cache / "finite_baseline.npy", mmap_mode="r")[box.lat0:box.lat1, box.lon0:box.lon1])
