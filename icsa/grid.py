"""The SST grid and day axis that every module shares.

Copernicus Marine SST-BAL-SST-L4-REP-OBSERVATIONS-010-016, variable
`analysed_sst`: 1051 lon x 626 lat at 0.02 deg over 9-30 E, 53.5-66 N, daily
from 1982-01-01 to 2023-12-31. Indices are 0-based. Cell (j, i) is lat
index j, lon index i, so arrays are shaped (day, lat, lon).

The coordinate origin below is nominal (cell centres on the 0.02 deg lattice,
both domain edges included). The ingest (#3) checks it against the product's
own coordinate variables; if they differ, fix it here, in one place.
"""
from __future__ import annotations

import datetime as dt
import operator

NLAT = 626
NLON = 1051
RES_DEG = 0.02
LAT_MIN = 53.5
LON_MIN = 9.0

DAY0 = dt.date(1982, 1, 1)
LAST_DAY = dt.date(2023, 12, 31)
NDAYS = 15340

# Baseline of the published catalogue (Bashiri et al. 2025): 4,018 days.
BASELINE = (dt.date(1992, 1, 1), dt.date(2002, 12, 31))
# Days on which the published domain events can start or end.
DETECTION_WINDOW = (dt.date(1982, 1, 2), dt.date(2023, 12, 30))
# Target periods of the instances (#5) are drawn from this window.
TARGET_WINDOW = (dt.date(2003, 1, 1), dt.date(2023, 12, 30))


def day_index(d: dt.date) -> int:
    """Index of a date on the day axis; raises if outside the product."""
    i = (d - DAY0).days
    if not 0 <= i < NDAYS:
        raise ValueError(f"{d} is outside {DAY0}..{LAST_DAY}")
    return i


def day_date(i: int) -> dt.date:
    """Date of a day index; accepts NumPy integers, rejects floats."""
    i = operator.index(i)
    if not 0 <= i < NDAYS:
        raise ValueError(f"day index {i} is outside 0..{NDAYS - 1}")
    return DAY0 + dt.timedelta(days=i)


def day_range(start: dt.date, end: dt.date) -> range:
    """Day indices from start to end, both inclusive."""
    a, b = day_index(start), day_index(end)
    if b < a:
        raise ValueError(f"empty period {start}..{end}")
    return range(a, b + 1)


def lat_of(j: int) -> float:
    return round(LAT_MIN + j * RES_DEG, 6)


def lon_of(i: int) -> float:
    return round(LON_MIN + i * RES_DEG, 6)


def lat_index(lat: float) -> int:
    """Index of the cell centre nearest to `lat`; raises outside the grid."""
    j = round((lat - LAT_MIN) / RES_DEG)
    if not 0 <= j < NLAT:
        raise ValueError(f"lat {lat} is outside the grid")
    return j


def lon_index(lon: float) -> int:
    i = round((lon - LON_MIN) / RES_DEG)
    if not 0 <= i < NLON:
        raise ValueError(f"lon {lon} is outside the grid")
    return i
