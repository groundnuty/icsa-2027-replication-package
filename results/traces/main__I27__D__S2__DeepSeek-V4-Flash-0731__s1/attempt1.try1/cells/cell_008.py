
import numpy as np
import pandas as pd

baseline_arr = np.load('/work/baseline_arr.npy')
target_arr = np.load('/work/target_arr.npy')
baseline_time = np.load('/work/baseline_time.npy').astype('datetime64[D]')
target_time = np.load('/work/target_time.npy').astype('datetime64[D]')

def date_to_doy(dt):
    d = pd.Timestamp(dt)
    month, day = d.month, d.day
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[month-1] + day

# Baseline period: 1992-01-01 to 2002-12-31
baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')

# All baseline dates
baseline_dates = pd.date_range(baseline_start, baseline_end, freq='D')
print("Number of baseline dates:", len(baseline_dates))

# For each doy d (1-366), find which baseline dates have that doy
# and which total dates (within ±5 days) contribute to the pool
doy_to_dates = {}  # doy -> list of dates (as datetime64) in the pool

# For each day-of-year d
for d in range(1, 367):
    if d == 60:
        continue  # day 60 gets no pool
    
    # Find baseline dates with this doy
    dates_with_doy = [bd for bd in baseline_dates if date_to_doy(bd) == d]
    
    # For each such date, include ±5 calendar days
    pool_dates = set()
    for bd in dates_with_doy:
        for offset in range(-5, 6):
            pool_dates.add(np.datetime64(bd) + np.timedelta64(offset, 'D'))
    
    doy_to_dates[d] = sorted(pool_dates)

# Check: what dates are in the pools?
# Check day 1
print("Day 1 pool dates:", doy_to_dates[1][:10], "...", doy_to_dates[1][-10:])
print("Day 366 pool dates:", doy_to_dates[366][:10], "...", doy_to_dates[366][-10:])
print("Day 59 pool dates (should include Feb 29 of leap years):", doy_to_dates[59][:15], "...")
print("Day 61 pool dates:", doy_to_dates[61][:15])

# Check that all pool dates are within our loaded data range
all_pool_dates = set()
for d in range(1, 367):
    if d != 60:
        all_pool_dates.update(doy_to_dates[d])
min_d = min(all_pool_dates)
max_d = max(all_pool_dates)
print("Pool date range:", min_d, "to", max_d)
print("Loaded data range:", baseline_time[0], "to", baseline_time[-1])
