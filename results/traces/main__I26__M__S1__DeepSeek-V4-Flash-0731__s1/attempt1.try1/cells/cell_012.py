
import numpy as np
import datetime
from collections import defaultdict

# Build pool dates for each doy
def date_to_doy(d):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = d.day
    for m in range(1, d.month):
        doy += days_in_month[m-1]
    return doy

# Baseline dates in 1992-2002
base_dates = np.load('base_dates.npy')
base_dates = [datetime.date.fromordinal(int(x)) for x in base_dates]
baseline_dates = [d for d in base_dates if 1992 <= d.year <= 2002]

# Build pool for each doy (excluding 60)
pool_dates = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    dates_in_pool = set()
    for bd in baseline_dates:
        if date_to_doy(bd) == doy:
            for offset in range(-5, 6):
                dates_in_pool.add(bd + datetime.timedelta(days=offset))
    pool_dates[doy] = sorted(dates_in_pool)

# Check some pools
for doy in [1, 59, 61, 180, 365, 366]:
    dates = pool_dates[doy]
    print(f"doy={doy}: {len(dates)} dates, first={dates[0]}, last={dates[-1]}")

# Check that pool dates are within our baseline data range
all_pool_dates = set()
for doy, dates in pool_dates.items():
    all_pool_dates.update(dates)
    
base_set = set(base_dates)
missing = all_pool_dates - base_set
print(f"\nTotal pool dates: {len(all_pool_dates)}")
print(f"Missing from baseline data: {len(missing)}")
if missing:
    print(f"First few missing: {sorted(missing)[:10]}")
