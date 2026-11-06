
import numpy as np
import xarray as xr
import pandas as pd
from datetime import datetime

# Load baseline data
baseline_data = xr.open_dataset('baseline_data.nc')
baseline_time = baseline_data.time.values
baseline_dates = [pd.Timestamp(t).to_pydatetime() for t in baseline_time]

def day_of_year(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month] + day

base_start = datetime(1992, 1, 1)
base_end = datetime(2002, 12, 31)

doy_to_indices = {}
for d in range(1, 367):
    if d == 60:
        continue
    pool_indices = set()
    for i, dt in enumerate(baseline_dates):
        if base_start <= dt <= base_end and day_of_year(dt) == d:
            for j in range(max(0, i-5), min(len(baseline_dates), i+6)):
                pool_indices.add(j)
    doy_to_indices[d] = sorted(pool_indices)

# Check pool sizes
sizes = {}
for d in range(1, 367):
    if d == 60:
        continue
    sizes[d] = len(doy_to_indices[d])

unique_sizes = set(sizes.values())
print(f"Unique pool sizes: {unique_sizes}")
for s in sorted(unique_sizes):
    days = [d for d, sz in sizes.items() if sz == s]
    print(f"  Size {s}: days {min(days)}-{max(days)}, count={len(days)}")
    if len(days) > 2:
        print(f"    Days: {days[:3]}...{days[-3:]}")
