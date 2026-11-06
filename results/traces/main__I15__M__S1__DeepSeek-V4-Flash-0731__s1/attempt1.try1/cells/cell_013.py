import numpy as np
from datetime import datetime, timedelta

# Baseline dates (1992-01-01 to 2002-12-31)
base_start = datetime(1992, 1, 1)
base_end = datetime(2002, 12, 31)

def day_of_year(date):
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[date.month - 1] + date.day

# All baseline dates
base_dates = []
d = base_start
while d <= base_end:
    base_dates.append(d)
    d += timedelta(days=1)

# Group baseline dates by day of year
from collections import defaultdict
doy_to_base_dates = defaultdict(list)
for date in base_dates:
    doy = day_of_year(date)
    doy_to_base_dates[doy].append(date)

# For each day of year, compute the pool dates
all_base_dates_set = set()
for date in base_dates:
    all_base_dates_set.add(date)

# Extended range dates
ext_start = datetime(1991, 12, 27)
ext_end = datetime(2003, 1, 5)
all_ext_dates = []
d = ext_start
while d <= ext_end:
    all_ext_dates.append(d)
    d += timedelta(days=1)

# For each doy (1-366, excluding 60), compute the pool dates
doy_to_pool_dates = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool_dates = set()
    for base_date in doy_to_base_dates.get(doy, []):
        for offset in range(-5, 6):
            date = base_date + timedelta(days=offset)
            # Include only if in extended range
            if ext_start <= date <= ext_end:
                pool_dates.add(date)
    doy_to_pool_dates[doy] = sorted(pool_dates)

# Check sizes
for doy in [1, 2, 59, 61, 100, 200, 300, 365, 366]:
    dates = doy_to_pool_dates.get(doy, [])
    print(f"DOY {doy}: {len(dates)} dates, first={dates[0] if dates else 'N/A'}, last={dates[-1] if dates else 'N/A'}")

# Check DOY 60 has no pool
print(f"DOY 60 pool size: {len(doy_to_pool_dates.get(60, []))}")
