
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import pickle

# Load data
sst_data = np.load('/tmp/sst_data.npy')
times_int = np.load('/tmp/times.npy')
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')

times = pd.to_datetime(times_int, unit='D')
n_times = len(times)

def compute_doy(month, day):
    if month == 1:
        return day
    elif month == 2:
        return 31 + day
    else:
        days_before = 60
        days_in_month = {3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}
        for m in range(3, month):
            days_before += days_in_month[m]
        return days_before + day

doy_all = np.array([compute_doy(t.month, t.day) for t in times], dtype=np.int32)

# Baseline and extended ranges
baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')
ext_start = np.datetime64('1991-12-27')
ext_end = np.datetime64('2003-01-05')

# Convert times to numpy datetime64 for comparison
times_np = times.values  # datetime64[ns]

# Find extended range indices
ext_mask = (times_np >= ext_start) & (times_np <= ext_end)
ext_indices = np.where(ext_mask)[0]

# Build pools: for each doy d (1-366, d != 60), list of dataset time indices
pools = {d: [] for d in range(1, 367) if d != 60}

# For each date t in extended range, find baseline dates within ±5 days
# A date t belongs to pool d if there's a baseline date b with doy(b)=d and |t-b|<=5

# We'll iterate over ext_indices and for each, check the window [t-5, t+5]
for t_idx in ext_indices:
    t = times_np[t_idx]
    win_start = t - np.timedelta64(5, 'D')
    win_end = t + np.timedelta64(5, 'D')
    # Find baseline dates in window
    # Use searchsorted on times_np
    lo = np.searchsorted(times_np, win_start, side='left')
    hi = np.searchsorted(times_np, win_end, side='right')
    for j in range(lo, hi):
        # Check if j is a baseline date
        if baseline_start <= times_np[j] <= baseline_end:
            d = doy_all[j]
            if d != 60:
                pools[d].append(t_idx)

# Convert lists to arrays
for d in pools:
    pools[d] = np.array(pools[d], dtype=np.int32)

# Print pool sizes
for d in [1, 59, 61, 153, 183, 244, 366]:
    print(f"Pool size for doy {d}: {len(pools[d])}")

# Save pools
with open('/tmp/pools.pkl', 'wb') as f:
    pickle.dump(pools, f)

print("Pools built and saved")
