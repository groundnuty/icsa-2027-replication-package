
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

baseline_arr = np.load('/work/baseline_arr.npy')
baseline_time = np.load('/work/baseline_time.npy').astype('datetime64[D]')
target_arr = np.load('/work/target_arr.npy')
target_time = np.load('/work/target_time.npy').astype('datetime64[D]')
lat = np.load('/work/lat.npy')
lon = np.load('/work/lon.npy')

def date_to_doy(dt):
    d = pd.Timestamp(dt)
    month, day = d.month, d.day
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[month-1] + day

# Identify sea cells
sea_mask = np.all(np.isfinite(target_arr), axis=0)
n_sea = sea_mask.sum()
print("Sea cells:", n_sea)

# Build a lookup from date to index in baseline array
date_to_idx = {}
for i, t in enumerate(baseline_time):
    date_to_idx[t] = i

# Baseline period dates
baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')
baseline_dates = pd.date_range(baseline_start, baseline_end, freq='D')

# For each doy d (1-366 except 60), compute the pool indices
doy_to_pool_indices = {}
for d in range(1, 367):
    if d == 60:
        continue
    dates_with_doy = [bd for bd in baseline_dates if date_to_doy(bd) == d]
    pool_dates = set()
    for bd in dates_with_doy:
        for offset in range(-5, 6):
            pool_dates.add(np.datetime64(bd) + np.timedelta64(offset, 'D'))
    # Convert to indices in baseline array
    idx = [date_to_idx[t] for t in sorted(pool_dates)]
    doy_to_pool_indices[d] = np.array(idx)

# Check sizes
for d in [1, 59, 61, 180, 366]:
    print(f"Day {d}: {len(doy_to_pool_indices[d])} pool dates")
