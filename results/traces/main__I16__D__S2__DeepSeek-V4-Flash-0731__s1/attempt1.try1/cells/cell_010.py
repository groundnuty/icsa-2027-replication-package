
import numpy as np
from datetime import date, timedelta

def day_of_year(month, day):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[month-1] + day

base_start = date(1992, 1, 1)
base_end = date(2002, 12, 31)
D_start = date(1991, 12, 27)
D_end = date(2003, 1, 5)

base_dates = []
d = base_start
while d <= base_end:
    base_dates.append(d)
    d += timedelta(days=1)
base_doy = {d: day_of_year(d.month, d.day) for d in base_dates}

# Check Feb 29 dates and their pools
for year in [1992, 1996, 2000]:
    D = date(year, 2, 29)
    pools = set()
    for B in base_dates:
        if abs((D - B).days) <= 5:
            pools.add(base_doy[B])
    print(D, "->", sorted(pools))

# Check what contributes to pool 60
# pool 60 = dates D within ±5 of a baseline date B with doy(B)=60
# baseline dates with doy 60: Feb 29 in 1992, 1996, 2000 (leap years in baseline)
for year in [1992, 1996, 2000]:
    B = date(year, 2, 29)
    D_start_local = B - timedelta(days=5)
    D_end_local = B + timedelta(days=5)
    print(f"Baseline date {B} (doy 60) window: {D_start_local} to {D_end_local}")
