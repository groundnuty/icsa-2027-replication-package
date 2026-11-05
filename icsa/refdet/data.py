"""Published fields, sea mask and SST readers for the reference detector."""
from __future__ import annotations

import datetime as dt
import functools
import glob
import re
from pathlib import Path

import netCDF4

from icsa.ncio import NETCDF_LOCK
import numpy as np

from .. import grid, paths
from ..extent import CellBox

SUPP_NAME = "BALMHW_supp.nc"
MASK_GLOB = "code_unzipped/*/mask_bathy/BAL-MFC_003_011_mask_bathy.nc"


def _ref(*parts: str) -> Path:
    return paths.REF.joinpath("bashiri", *parts)


@functools.lru_cache(maxsize=1)
def _full_sea_mask() -> np.ndarray:
    """The BAL-MFC_003_011 bathymetry mask on the SST grid (626, 1051): nearest cell,
    NaN (land or outside the mask grid) = False. Step_1 does `interpn(..., 'nearest')`
    on `deptho` set to 1 where finite."""
    hits = sorted(glob.glob(str(_ref(MASK_GLOB))))
    if not hits:
        raise FileNotFoundError(f"bathymetry mask not found under {_ref()}")
    with NETCDF_LOCK, netCDF4.Dataset(hits[0]) as d:
        deptho = np.ma.filled(d["deptho"][:].astype(np.float64), np.nan)
        mlat = np.asarray(d["latitude"][:], np.float64)
        mlon = np.asarray(d["longitude"][:], np.float64)
    sea = np.isfinite(deptho)
    lat = grid.LAT_MIN + np.arange(grid.NLAT) * grid.RES_DEG
    lon = grid.LON_MIN + np.arange(grid.NLON) * grid.RES_DEG
    ji = _nearest(mlat, lat)
    ii = _nearest(mlon, lon)
    out = sea[np.ix_(np.where(ji >= 0, ji, 0), np.where(ii >= 0, ii, 0))]
    out &= (ji >= 0)[:, None] & (ii >= 0)[None, :]
    return out


def _nearest(axis: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Index of the nearest axis point for each x (axis uniform, increasing); -1 outside the axis range."""
    step = (axis[-1] - axis[0]) / (axis.size - 1)
    f = (x - axis[0]) / step
    idx = np.floor(f + 0.5).astype(np.int64)  # MATLAB rounds half up for positive indices
    bad = (f < -1e-9) | (f > axis.size - 1 + 1e-9)
    return np.where(bad, -1, np.clip(idx, 0, axis.size - 1))


def sea_mask(box: CellBox) -> np.ndarray:
    m = _full_sea_mask()
    return m[box.lat0:box.lat1, box.lon0:box.lon1].copy()


@functools.lru_cache(maxsize=1)
def _supp_path() -> Path:
    p = _ref("data", SUPP_NAME)
    if not p.exists():
        raise FileNotFoundError(f"{p} not present (published fields, mode a)")
    return p


def published_arrays(box: CellBox) -> tuple[np.ndarray, np.ndarray]:
    with NETCDF_LOCK:
        return _published_arrays(box)


def _published_arrays(box: CellBox) -> tuple[np.ndarray, np.ndarray]:
    """(m90, mclim) float32 (366, h, w) cut from BALMHW_supp.nc to `box`.

    The file stores (time, lat, lon) after netCDF4 reads it; asserted, because MATLAB
    wrote [lon, lat, time] in column-major order.
    """
    with netCDF4.Dataset(_supp_path()) as d:
        outs = []
        for name in ("m90", "mclim"):
            v = d[name]
            dims = v.dimensions
            sl = {"time": slice(None), "latitude": slice(box.lat0, box.lat1),
                  "longitude": slice(box.lon0, box.lon1)}
            a = np.ma.filled(v[tuple(sl[x] for x in dims)], np.nan).astype(np.float32)
            order = [dims.index(x) for x in ("time", "latitude", "longitude")]
            outs.append(np.ascontiguousarray(np.transpose(a, order)))
    return outs[0], outs[1]


_DATE_RE = re.compile(r"(\d{4})-?(\d{2})-?(\d{2})")


def _read_var(ds: netCDF4.Dataset, box: CellBox, idx) -> np.ndarray:
    v = ds["analysed_sst"]
    dims = v.dimensions
    sl = []
    for name in dims:
        if name.startswith("lat"):
            sl.append(slice(box.lat0, box.lat1))
        elif name.startswith("lon"):
            sl.append(slice(box.lon0, box.lon1))
        else:
            sl.append(idx)
    a = np.ma.filled(v[tuple(sl)], np.nan).astype(np.float32)
    return a


def s1_index(s1_dir=None) -> dict[dt.date, Path]:
    """Date -> S1 daily file, the one resolver both the reader and the field-cache fingerprint use.
    Any `.nc` file whose name carries YYYY-MM-DD or YYYYMMDD counts. Two files for one date raise
    ValueError, so the fingerprint can never track a different file from the one the reader opens."""
    s1_dir = Path(s1_dir or paths.S1_DIR)
    index: dict[dt.date, Path] = {}
    for p in sorted(s1_dir.iterdir()):
        m = _DATE_RE.search(p.name)
        if m and p.suffix == ".nc":
            d = dt.date(*map(int, m.groups()))
            if d in index:
                raise ValueError(f"two S1 files for {d}: {index[d].name} and {p.name}")
            index[d] = p
    return index


def s1_file(index: dict[dt.date, Path], day: int) -> Path:
    """The S1 file of a global day index; a missing day raises FileNotFoundError."""
    p = index.get(grid.day_date(int(day)))
    if p is None:
        raise FileNotFoundError(f"no S1 file for {grid.day_date(int(day))}")
    return p


def load_sst(box: CellBox, days: np.ndarray, source: str = "s1") -> np.ndarray:
    with NETCDF_LOCK:                          # netCDF4/HDF5 is not thread-safe
        return _load_sst(box, days, source)


def _load_sst(box: CellBox, days: np.ndarray, source: str = "s1") -> np.ndarray:
    """SST in kelvin, float32, NaN on land, shaped (len(days), h, w).

    source "s1": the daily files in `paths.S1_DIR`, resolved by `s1_index` (any file name carrying
    YYYY-MM-DD or YYYYMMDD; two files for one date raise). source "raw": the yearly download in
    `paths.RAW`, found by its time axis.
    Days not found raise, so a hole in the data cannot pass as "no data".
    """
    days = np.asarray(days, dtype=np.int64)
    out = np.full((days.size, *box.shape), np.nan, np.float32)
    if source == "s1":
        index = s1_index(paths.S1_DIR)
        for k, d in enumerate(days):
            p = s1_file(index, d)
            with netCDF4.Dataset(p) as ds:
                a = _read_var(ds, box, 0 if ds["analysed_sst"].ndim == 3 else slice(None))
            out[k] = a.reshape(box.shape)
        return out
    if source == "raw":
        want = {grid.day_date(int(d)): k for k, d in enumerate(days)}
        found: set[int] = set()     # which requested days, not how many records: two files can hold one day
        for p in sorted(Path(paths.RAW).glob("**/*.nc")):
            with netCDF4.Dataset(p) as ds:
                if "analysed_sst" not in ds.variables:
                    continue
                t = ds["time"]
                dates = netCDF4.num2date(t[:], t.units, only_use_cftime_datetimes=False,
                                         only_use_python_datetimes=True)
                for ti, dd in enumerate(dates):
                    k = want.get(dt.date(dd.year, dd.month, dd.day))
                    if k is not None:
                        out[k] = _read_var(ds, box, ti)
                        found.add(k)
        if len(found) != len(want):
            raise FileNotFoundError(f"raw download has {len(found)} of {len(want)} requested days")
        return out
    raise ValueError(f"unknown source {source!r}")
