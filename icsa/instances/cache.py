"""One streaming pass that cuts the 25 boxes out of S1 into per-box memmaps.

Days 1991-12-27..2023-12-30 (12,050 days), float32 K, NaN where missing.
Output: <ICSA_DATA>/instances/boxsst/box<NN>.npy, shape (12050, h, w).
Memory: the 25 memmaps are written through the page cache; one day in RAM.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import netCDF4

from icsa.ncio import NETCDF_LOCK
import numpy as np

from .. import grid, paths
from ..extent import CellBox
from .seascan import BASE_START, s1_index

LAST = dt.date(2023, 12, 30)
FIRST_IDX = grid.day_index(BASE_START)
NCACHE = grid.day_index(LAST) - FIRST_IDX + 1


def cache_dir() -> Path:
    return Path(paths.DATA_ROOT) / "instances" / "boxsst"


def _read(p: Path) -> np.ndarray:
    with NETCDF_LOCK, netCDF4.Dataset(p) as ds:
        a = np.ma.filled(ds["analysed_sst"][...].astype(np.float32), np.nan)
    return a.reshape(grid.NLAT, grid.NLON)


def build(boxes: list[CellBox]) -> None:
    d = cache_dir()
    d.mkdir(parents=True, exist_ok=True)
    idx = s1_index()
    mm = [np.lib.format.open_memmap(d / f"box{k:02d}.npy", "w+", np.float32, (NCACHE, *b.shape))
          for k, b in enumerate(boxes)]
    days = [BASE_START + dt.timedelta(n) for n in range(NCACHE)]
    for n, day in enumerate(days):  # sequential: netCDF4/HDF5 is not thread-safe
        a = _read(idx[day])
        for m, b in zip(mm, boxes):
            m[n] = a[b.lat0:b.lat1, b.lon0:b.lon1]
    for m in mm:
        m.flush()


def load(k: int, days: np.ndarray) -> np.ndarray:
    """SST (len(days), h, w) of box k, from the cache; days are global indices."""
    m = np.load(cache_dir() / f"box{k:02d}.npy", mmap_mode="r")
    return np.asarray(m[np.asarray(days) - FIRST_IDX])
