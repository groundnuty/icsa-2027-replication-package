"""Shared ingest pieces: raw reader, decoding, file naming for S1/S2.

Raw files (`SST_BAL_<year>.nc`, from icsa.ingest.download) hold `analysed_sst` as
int16 with scale_factor / add_offset / _FillValue=-32768 (kelvin). Decoding is
float32(raw * scale_factor + add_offset) computed in float64, land (fill) = NaN.
raw values outside [valid_min, valid_max] (CF valid_range semantics; the source has
122 cells holding 9900 > valid_max, all in 1982) also become NaN (science decision, issue #3).
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Iterator, NamedTuple

import netCDF4
import numpy as np

from icsa import grid
from icsa.paths import RAW, S1_DIR

VAR = "analysed_sst"
FILL_RAW = -32768
TIME_UNITS = "seconds since 1981-01-01"
TIME_EPOCH = dt.datetime(1981, 1, 1)
DATASET_ID = "cmems_obs-sst_bal_phy-temp_my_l4_P1D-m"
PRODUCT_ID = "SST_BAL_SST_L4_REP_OBSERVATIONS_010_016"
DOI = "10.48670/moi-00156"
DATASET_VERSION = "202506"
DOWNLOAD_DATE = "2026-10-31"
COMPLEVEL = 4   # deflate level, no shuffle, no other filter (operator decision on #3)
ATTRIBUTION = ("Generated using E.U. Copernicus Marine Service Information; "
               "https://doi.org/10.48670/moi-00156")


def s1_name(d: dt.date) -> str:
    return f"sst_{d:%Y%m%d}.nc"


def s1_path(d: dt.date, root: Path = S1_DIR) -> Path:
    return root / s1_name(d)


def time_seconds(d: dt.date) -> int:
    return int((dt.datetime(d.year, d.month, d.day) - TIME_EPOCH).total_seconds())


def decode(raw: np.ndarray, scale: float, offset: float, vmin: int, vmax: int) -> np.ndarray:
    out = (raw.astype(np.float64) * scale + offset).astype(np.float32)
    out[(raw == FILL_RAW) | (raw < vmin) | (raw > vmax)] = np.nan
    return out


def raw_year_path(year: int, raw_dir: Path = RAW) -> Path:
    return raw_dir / f"SST_BAL_{year}.nc"


def read_coords(raw_dir: Path = RAW):
    """Lat/lon float32 coordinate vectors from the first raw file."""
    with netCDF4.Dataset(raw_year_path(grid.DAY0.year, raw_dir)) as ds:
        return np.asarray(ds["latitude"][:]), np.asarray(ds["longitude"][:])


class Packing(NamedTuple):
    scale: float
    offset: float
    vmin: int
    vmax: int


def iter_days(first: dt.date = grid.DAY0, last: dt.date = grid.LAST_DAY,
              raw_dir: Path = RAW) -> Iterator[tuple[dt.date, np.ndarray, Packing]]:
    """Yield (date, raw int16 (lat, lon), Packing) for each day, in order.

    Checks each raw time stamp against the expected date.
    """
    for year in range(first.year, last.year + 1):
        with netCDF4.Dataset(raw_year_path(year, raw_dir)) as ds:
            v = ds[VAR]
            v.set_auto_maskandscale(False)
            pk = Packing(float(v.scale_factor), float(v.add_offset), int(v.valid_min), int(v.valid_max))
            t = ds["time"][:]
            n = v.shape[0]
            for k in range(n):
                d = dt.date(year, 1, 1) + dt.timedelta(days=k)
                if d < first or d > last:
                    continue
                if int(t[k]) != time_seconds(d):
                    raise ValueError(f"{raw_year_path(year, raw_dir)}: time[{k}]={int(t[k])} != {d}")
                yield d, np.asarray(v[k]), pk
