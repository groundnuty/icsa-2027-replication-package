import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

def day_of_year(date):
    """Map date to day of year 1-366 by month and day."""
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[date.month - 1] + date.day

# Baseline dates (1992-01-01 to 2002-12-31)
base_start = datetime(1992, 1, 1)
base_end = datetime(2002, 12, 31)

# Extended range (data available)
ext_start = datetime(1991, 12, 27)
ext_end = datetime(2003, 1, 5)

# All baseline dates
base_dates = []
d = base_start
while d <= base_end:
    base_dates.append(d)
    d += timedelta(days=1)

# Group baseline dates by day of year
doy_to_base_dates = defaultdict(list)
for date in base_dates:
    doy = day_of_year(date)
    doy_to_base_dates[doy].append(date)

# For each doy (1-366, excluding 60), compute the pool dates
doy_to_pool_dates = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool_dates = set()
    for base_date in doy_to_base_dates.get(doy, []):
        for offset in range(-5, 6):
            date = base_date + timedelta(days=offset)
            if ext_start <= date <= ext_end:
                pool_dates.add(date)
    doy_to_pool_dates[doy] = sorted(pool_dates)

# Save for later use
import pickle
with open('/tmp/doy_pool_dates.pkl', 'wb') as f:
    pickle.dump(doy_to_pool_dates, f)

# Verify a few pools
for doy in [1, 2, 59, 61, 100, 200, 300, 365, 366]:
    dates = doy_to_pool_dates.get(doy, [])
    print(f"DOY {doy}: {len(dates)} dates, first={dates[0].strftime('%Y-%m-%d') if dates else 'N/A'}, last={dates[-1].strftime('%Y-%m-%d') if dates else 'N/A'}")

# Check DOY 60 has no pool
print(f"DOY 60 pool size: {len(doy_to_pool_dates.get(60, []))}")

# Check: DOY 1 should include 1991-12-27 (since 1992-01-01 - 5 days = 1991-12-27)
doy1 = doy_to_pool_dates[1]
print("DOY 1 first date:", doy1[0].strftime('%Y-%m-%d'))
print("DOY 1 last date:", doy1[-1].strftime('%Y-%m-%d'))
print("1991-12-27 in pool?", datetime(1991, 12, 27) in doy1)
print("2003-01-06 in pool?", datetime(2003, 1, 6) in doy1)
print("2003-01-05 in pool?", datetime(2003, 1, 5) in doy1)
