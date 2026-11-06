
import numpy as np
from datetime import date, timedelta

def day_of_year(month, day):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[month-1] + day

# Build the baseline date range and window
# Baseline dates: 1992-01-01 to 2002-12-31
# All D dates: 1991-12-27 to 2003-01-05

base_start = date(1992, 1, 1)
base_end = date(2002, 12, 31)
D_start = date(1991, 12, 27)
D_end = date(2003, 1, 5)

# For each date D, find baseline dates B with |D-B|<=5
# and get their doys
from collections import defaultdict

# Precompute doy for all baseline dates
base_dates = []
d = base_start
while d <= base_end:
    base_dates.append(d)
    d += timedelta(days=1)

base_doy = {d: day_of_year(d.month, d.day) for d in base_dates}

# For each D, determine which pools it contributes to
D_date = D_start
D_pools = {}  # date -> list of doys

while D_date <= D_end:
    pools = set()
    for B in base_dates:
        if abs((D_date - B).days) <= 5:
            pools.add(base_doy[B])
    D_pools[D_date] = sorted(pools)
    D_date += timedelta(days=1)

# Verify some samples
for D in [date(1991,12,27), date(1991,12,31), date(1992,1,1), date(1992,1,6),
          date(1992,2,28), date(1992,2,29), date(2002,12,31), date(2003,1,1), date(2003,1,5)]:
    print(D, "->", D_pools[D])
