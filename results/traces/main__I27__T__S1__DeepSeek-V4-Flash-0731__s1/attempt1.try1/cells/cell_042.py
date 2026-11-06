
import numpy as np
import pandas as pd
import datetime

# Load data
baseline_data = np.load('/tmp/baseline_data.npy')
baseline_times = pd.DatetimeIndex(np.load('/tmp/baseline_times.npy').astype('datetime64[ns]'))

def date_to_doy(dt):
    days_in_month_fixed = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month_fixed[:dt.month]) + dt.day

# Get the array of dates for the full loaded baseline
all_dates = [pd.Timestamp(t) for t in baseline_times]

# Build a dict mapping each date (as Timestamp) to its index in baseline_data
date_to_idx = {d: i for i, d in enumerate(all_dates)}

# Baseline period for pool construction
baseline_start = pd.Timestamp('1992-01-01')
baseline_end = pd.Timestamp('2002-12-31')

# For each day of year d (1-366, except 60), find the indices of all dates
# in all_dates that belong to the pool for d.
# The pool for d = all dates within ±5 calendar days of any baseline date with doy = d.

# First, identify which dates in all_dates are "baseline dates with doy = d"
# Actually, we need to find the windows.

# Strategy:
# For each day of year d:
#   For each year Y in 1992-2002:
#     Find the date in year Y with doy = d (this date is in the baseline period)
#     The window is [date - 5 days, date + 5 days]
#   The pool indices are all indices whose date falls in any of these windows

# Precompute for each day of year the set of pool indices
pool_indices_by_doy = {}

for doy in range(1, 367):
    if doy == 60:
        continue  # No pool for day 60
    
    # Find all baseline dates with this doy
    # These are dates in 1992-2002 with date_to_doy == doy
    window_dates = set()
    for date in all_dates:
        if baseline_start <= date <= baseline_end and date_to_doy(date) == doy:
            # Add the ±5 day window
            for delta in range(-5, 6):
                window_date = date + pd.Timedelta(days=delta)
                if window_date in date_to_idx:
                    window_dates.add(date_to_idx[window_date])
    
    pool_indices_by_doy[doy] = sorted(window_dates)

# Check pool sizes
for doy in [1, 59, 60, 61, 100, 366]:
    if doy != 60:
        print(f"DOY {doy}: pool size = {len(pool_indices_by_doy[doy])}")
    else:
        print(f"DOY 60: no pool (will use mean of 59 and 61)")

# Verify: pool for day 1 should include dates from 1991-12-27 to 2003-01-06 roughly
print(f"\nDOY 1 pool dates: {all_dates[pool_indices_by_doy[1][0]]} to {all_dates[pool_indices_by_doy[1][-1]]}")
print(f"DOY 1 pool dates count: {len(pool_indices_by_doy[1])}")

# Check if any pool includes dates outside the baseline range
for doy in [1, 59, 61, 366]:
    indices = pool_indices_by_doy[doy]
    if indices:
        first_date = all_dates[indices[0]]
        last_date = all_dates[indices[-1]]
        print(f"DOY {doy}: dates from {first_date} to {last_date}")

# Save pool indices
import pickle
with open('/tmp/pool_indices.pkl', 'wb') as f:
    pickle.dump(pool_indices_by_doy, f)
print("\nPool indices saved")
