"""Streaming sea-cell scan (#5).

A cell is sea for an instance iff its S1 SST is finite on every day of the
baseline-with-neighbours 1991-12-27..2003-01-05 AND of the target period (the
prompt's definition; no bathymetry mask). One pass over the days holds only
boolean accumulators of shape (626, 1051): one for the baseline and one per
(candidate period type, year). Target-period sea masks are then
`baseline & period_mask`.
"""
from __future__ import annotations

import calendar
import datetime as dt
import re
from pathlib import Path

import netCDF4
import numpy as np

from .. import grid, paths

BASE_START = dt.date(1991, 12, 27)
BASE_END = dt.date(2003, 1, 5)
FIRST_YEAR, LAST_YEAR = 2003, 2023
# candidate period types -> (first month, last month); "year" is Jan..Dec
KINDS = {"year": (1, 12), "mayseptember": (5, 9), "junaug": (6, 8)}
_DATE = re.compile(r"(\d{4})-?(\d{2})-?(\d{2})")


def period_days(kind: str, year: int) -> tuple[dt.date, dt.date]:
    m0, m1 = KINDS[kind]
    end = dt.date(year, m1, calendar.monthrange(year, m1)[1])
    if end > dt.date(2023, 12, 30):
        end = dt.date(2023, 12, 30)  # detection window ends 2023-12-30
    return dt.date(year, m0, 1), end


def s1_index() -> dict[dt.date, Path]:
    out = {}
    for p in Path(paths.S1_DIR).iterdir():
        m = _DATE.search(p.name)
        if m and p.suffix == ".nc":
            out[dt.date(*map(int, m.groups()))] = p
    return out


def read_finite(p: Path) -> np.ndarray:
    with netCDF4.Dataset(p) as ds:
        a = np.ma.filled(ds["analysed_sst"][...].astype(np.float32), np.nan)
    return np.isfinite(a.reshape(grid.NLAT, grid.NLON))


def scan() -> dict[str, np.ndarray]:
    idx = s1_index()
    days = [BASE_START + dt.timedelta(n) for n in range((dt.date(2023, 12, 30) - BASE_START).days + 1)]
    shape = (grid.NLAT, grid.NLON)
    acc = {"baseline": np.ones(shape, bool)}
    for kind in KINDS:
        for y in range(FIRST_YEAR, LAST_YEAR + 1):
            acc[f"{kind}:{y}"] = np.ones(shape, bool)
    ever = np.zeros(shape, bool)
    missing = [d for d in days if d not in idx]
    if missing:
        raise FileNotFoundError(f"{len(missing)} S1 days missing, first {missing[0]}")
    keys_of = {}
    for d in days:
        ks = []
        if BASE_START <= d <= BASE_END:
            ks.append("baseline")
        if FIRST_YEAR <= d.year <= LAST_YEAR:
            for kind, (m0, m1) in KINDS.items():
                if m0 <= d.month <= m1:
                    ks.append(f"{kind}:{d.year}")
        keys_of[d] = ks
    # netCDF4/HDF5 is not thread-safe (a thread pool segfaulted): read sequentially.
    for d in days:
        fin = read_finite(idx[d])
        for k in keys_of[d]:
            acc[k] &= fin
        ever |= fin
    acc["ever"] = ever
    return acc


if __name__ == "__main__":
    import sys
    out = Path(paths.DATA_ROOT) / "instances" / "seascan.npz"
    out.parent.mkdir(parents=True, exist_ok=True)
    acc = scan()
    np.savez_compressed(out, **{k.replace(":", "_"): v for k, v in acc.items()})
    print(out, {k: int(v.sum()) for k, v in list(acc.items())[:3]})
