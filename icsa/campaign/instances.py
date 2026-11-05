"""Instance loader. FIXTURE until #5 lands: one function to replace."""
from __future__ import annotations

import datetime as dt

from icsa.records import Instance, Period


def load_instances() -> list[Instance]:
    """50 fixture instances (25 regions x 2 periods); 10 flagged as pilot.

    FIXTURE: regions and periods are arbitrary. #5 replaces this body with the
    real instance set; callers only use the returned list.
    """
    out: list[Instance] = []
    for r in range(25):
        for p in range(2):
            lat0 = 20 * r
            lon0 = 30 * r
            year = 2012 + 4 * p
            out.append(Instance(
                instance_id=f"r{r:02d}p{p}", region_id=f"region{r:02d}",
                lat_min=53.0 + 0.02 * lat0, lat_max=53.0 + 0.02 * (lat0 + 20),
                lon_min=9.0 + 0.02 * lon0, lon_max=9.0 + 0.02 * (lon0 + 30),
                lat0=lat0, lat1=lat0 + 20, lon0=lon0, lon1=lon0 + 30,
                target=Period(dt.date(year, 1, 1), dt.date(year, 12, 31)),
                pilot=(p == 0 and r < 10),
                # one pilot instance carries #5's calibration flag; deliberately not the first
                calibration=(p == 0 and r == 3)))
    return out
