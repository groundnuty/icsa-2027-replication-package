"""Small synthetic SST files shaped like the Copernicus Baltic SST L4 product.

Used as test fixtures and validation data. Values depend only on the global
(day, lat index, lon index) and the seed, so the same unit has the same value
in every crop and in both layouts (S1: one file per day; S2: one file).
"""
from __future__ import annotations

import dataclasses
import datetime as dt
from pathlib import Path

import netCDF4
import numpy as np

from .. import grid
from ..extent import CellBox

_EPOCH = dt.date(1981, 1, 1)


@dataclasses.dataclass(frozen=True)
class SynthData:
    s1_dir: Path | None      # one file per day, one flat directory
    s2_file: Path | None     # one file, all days
    box: CellBox             # the crop, in global grid indices
    days: np.ndarray         # int64 sorted global day indices written
    land: np.ndarray         # bool (ny, nx), True = land (NaN on every day)


def _splitmix64(x: np.ndarray) -> np.ndarray:
    x = x + np.uint64(0x9E3779B97F4A7C15)
    x = (x ^ (x >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
    x = (x ^ (x >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
    return x ^ (x >> np.uint64(31))


def sst_value(days, lat_idx, lon_idx, seed=0) -> np.ndarray:
    """Synthetic SST in kelvin (float32), broadcasting over its arguments.

    No NaN handling: land is applied by the writer.
    """
    d = np.asarray(days, dtype=np.int64)
    la = np.asarray(lat_idx, dtype=np.int64)
    lo = np.asarray(lon_idx, dtype=np.int64)
    with np.errstate(over="ignore"):
        h = _splitmix64(np.uint64(seed & 0xFFFFFFFFFFFFFFFF) ^ d.astype(np.uint64))
        h = _splitmix64(h ^ la.astype(np.uint64))
        h = _splitmix64(h ^ lo.astype(np.uint64))
    noise = (h >> np.uint64(11)).astype(np.float64) / float(1 << 53) - 0.5
    v = (278.0 + 8.0 * np.sin(2 * np.pi * (d - 110.0) / 365.25)
         + 0.01 * la - 0.005 * lo + noise)
    return v.astype(np.float32)


def default_land(box: CellBox) -> np.ndarray:
    """Deterministic land mask: a corner block of about 15% of the cells."""
    ny, nx = box.shape
    land = np.zeros((ny, nx), bool)
    h = max(1, round(ny * 0.4))
    w = max(1, round(nx * 0.375))
    land[:h, :w] = True  # south-west block (0.4 * 0.375 = 15%)
    return land


def s1_name(day: int) -> str:
    return f"{grid.day_date(day):%Y%m%d}-SST-L4.nc"


def _time_seconds(day: int) -> float:
    return float((grid.day_date(day) - _EPOCH).days * 86400)


# The real S1/S2 (#3, operator decision 1 Nov): deflate level 4, no shuffle, one
# chunk per day (1, 626, 1051). Compressed chunks have variable byte lengths, so
# byte offsets map to days only through the file's own chunk index.
DEFLATE_LEVEL = 4


def _write_file(path: Path, ntime: int | None, days, lat_rows, lon0, ny, nx, data,
                compression: str | None = "deflate4") -> None:
    """data: float32 (len(days), ny, nx) already in file row order."""
    with netCDF4.Dataset(path, "w", format="NETCDF4") as ds:
        ds.Conventions = "CF-1.8"
        ds.title = "SYNTHETIC test data shaped like SST-BAL-SST-L4-REP-OBSERVATIONS-010-016"
        ds.source = "icsa.instruments.synth"
        ds.createDimension("time", ntime)
        ds.createDimension("lat", ny)
        ds.createDimension("lon", nx)
        t = ds.createVariable("time", "f8", ("time",))
        t.units = "seconds since 1981-01-01 00:00:00"
        t.calendar = "gregorian"
        t.standard_name = "time"
        t.axis = "T"
        la = ds.createVariable("lat", "f4", ("lat",))
        la.units, la.standard_name, la.axis = "degrees_north", "latitude", "Y"
        lo = ds.createVariable("lon", "f4", ("lon",))
        lo.units, lo.standard_name, lo.axis = "degrees_east", "longitude", "X"
        v = ds.createVariable("analysed_sst", "f4", ("time", "lat", "lon"),
                              zlib=compression is not None, complevel=DEFLATE_LEVEL,
                              shuffle=False, chunksizes=(1, ny, nx),
                              fill_value=np.float32(np.nan))
        v.units = "kelvin"
        v.standard_name = "sea_surface_foundation_temperature"
        v.long_name = "analysed sea surface temperature"
        v.valid_min = np.float32(250.0)
        v.valid_max = np.float32(320.0)
        t[:] = np.array([_time_seconds(int(d)) for d in days], dtype="f8")
        la[:] = np.array([grid.lat_of(lat_rows[k]) for k in range(ny)], dtype="f4")
        lo[:] = np.array([grid.lon_of(lon0 + k) for k in range(nx)], dtype="f4")
        v.set_auto_mask(False)
        v[:] = data


def write_synthetic(root: Path, box: CellBox, days, *, seed=0, land=None, s1=True, s2=True,
                    lat_descending=False, compression: str | None = "deflate4") -> SynthData:
    """`compression`: "deflate4" (as the real data) or None (uncompressed, for tests of
    the element-level byte mapping of unfiltered chunks)."""
    if compression not in ("deflate4", None):
        raise ValueError(compression)
    root = Path(root)
    days = np.asarray(list(days) if not isinstance(days, np.ndarray) else days)
    if days.size and not np.issubdtype(days.dtype, np.integer):
        raise TypeError("days must be integers")
    days = days.astype(np.int64)
    if days.size == 0:
        raise ValueError("days is empty")
    ny, nx = box.shape
    land = default_land(box) if land is None else np.asarray(land, bool)
    if land.shape != (ny, nx):
        raise ValueError(f"land shape {land.shape} != {(ny, nx)}")

    lat_rows = np.arange(box.lat0, box.lat1)
    if lat_descending:
        lat_rows = lat_rows[::-1]
    lat_list = [int(x) for x in lat_rows]
    row_land = land[lat_rows - box.lat0]
    lon_cols = np.arange(box.lon0, box.lon1)

    def block(ds: np.ndarray) -> np.ndarray:
        v = sst_value(ds[:, None, None], lat_rows[None, :, None], lon_cols[None, None, :], seed)
        v[:, row_land] = np.float32(np.nan)
        return v

    def write(path, ds, ntime):
        _write_file(path, ntime, ds, lat_list, box.lon0, ny, nx, block(ds), compression)

    s1_dir = s2_file = None
    if s1:
        s1_dir = root / "s1"
        s1_dir.mkdir(parents=True, exist_ok=True)
        for d in days:
            write(s1_dir / s1_name(int(d)), np.array([d]), None)
    if s2:
        (root / "s2").mkdir(parents=True, exist_ok=True)
        s2_file = root / "s2" / "sst_s2.nc"
        write(s2_file, days, len(days))
    return SynthData(s1_dir, s2_file, box, np.unique(days), land)
