
import numpy as np
import xarray as xr
from datetime import date, timedelta
import pandas as pd
from collections import defaultdict

# Load saved data
baseline_data = xr.open_dataset('baseline_data.nc')
target_data = xr.open_dataset('target_data.nc')

# Day of year mapping
cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def date_to_doy(year, month, day):
    return cum_days[month-1] + day

# All dates in the baseline dataset
all_dates_np = baseline_data.time.values.astype('datetime64[D]')
all_date_objs = [pd.Timestamp(t).date() for t in all_dates_np]

# Baseline period: 1992-01-01 to 2002-12-31
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)

# Baseline dates
baseline_date_objs = [d for d in all_date_objs if baseline_start <= d <= baseline_end]

# Group baseline dates by day of year
doy_to_baseline_dates = defaultdict(list)
for d in baseline_date_objs:
    doy = date_to_doy(d.year, d.month, d.day)
    doy_to_baseline_dates[doy].append(d)

# For each day of year d (1-366, excluding 60), find the indices in all_dates that belong to pool d
# A date t belongs to pool d if there exists a baseline date b with doy(b)=d and |t-b| <= 5 days

# Build date-to-index map
date_to_idx = {d: i for i, d in enumerate(all_date_objs)}

# For each day of year, collect the date indices in its pool
doy_to_date_indices = {}

for doy in range(1, 367):
    if doy == 60:
        continue
    pool_indices = set()
    for b in doy_to_baseline_dates.get(doy, []):
        # Window: b-5 to b+5
        for delta in range(-5, 6):
            t = b + timedelta(days=delta)
            if t in date_to_idx:
                pool_indices.add(date_to_idx[t])
    doy_to_date_indices[doy] = sorted(pool_indices)

# Check some pools
for doy in [1, 59, 61, 366]:
    idxs = doy_to_date_indices[doy]
    dates_in_pool = [all_date_objs[i] for i in idxs]
    print(f"DOY {doy}: {len(idxs)} dates in pool")
    print(f"  First 5: {dates_in_pool[:5]}")
    print(f"  Last 5: {dates_in_pool[-5:]}")
    print()

# Check DOY 365 (Dec 31 in non-leap years... but wait, Dec 31 = 366 always)
# Let me check DOY 59 (Feb 28)
print(f"DOY 59 pool size: {len(doy_to_date_indices[59])}")
print(f"DOY 61 pool size: {len(doy_to_date_indices[61])}")
