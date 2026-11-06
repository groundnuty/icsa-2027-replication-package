
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Load the data
baseline_sst = np.load('/work/baseline_sst.npy')
target_sst = np.load('/work/target_sst.npy')
base_times = np.load('/work/base_times.npy')
targ_times = np.load('/work/targ_times.npy')

# Convert times to datetime
base_dates = pd.DatetimeIndex(base_times)
targ_dates = pd.DatetimeIndex(targ_times)

print(f"Baseline data shape: {baseline_sst.shape}")
print(f"Target data shape: {target_sst.shape}")
print(f"Baseline dates: {base_dates[0]} to {base_dates[-1]}")
print(f"Target dates: {targ_dates[0]} to {targ_dates[-1]}")

# Day of year mapping
def date_to_doy(dt):
    """Map a datetime to day of year 1-366 as specified."""
    year, month, day = dt.year, dt.month, dt.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[m] for m in range(0, month-1)) + day
    return doy

# Compute doy for each baseline date
base_doy = np.array([date_to_doy(d) for d in base_dates])
print(f"Baseline doy range: {base_doy.min()} to {base_doy.max()}")

# Check: which doy values are present in baseline
unique_doy = np.unique(base_doy)
print(f"Unique doy in baseline: {len(unique_doy)}")
print(f"Missing doy: {sorted(set(range(1, 367)) - set(unique_doy))}")

# The baseline dates cover 1991-12-27 to 2003-01-05
# Baseline years are 1992-2002 for the pool building
# Dates with doy d in baseline years are 1992-01-01 to 2002-12-31
# But we need the ±5 day windows, which extend into 1991-12-27+ and 2003-01-05-

# The dates from 1991-12-27 to 1991-12-31 have doys in the 360s
# The dates from 2003-01-01 to 2003-01-05 have doys 1-5

# For the pool of doy d, we need dates within ±5 calendar days of any date 
# in 1992-01-01 to 2002-12-31 that has doy d.

# Let me check: for doy 1 (Jan 1), the baseline dates with doy 1 are Jan 1 of 1992-2002.
# Each Jan 1 has a ±5 day window: Dec 27 to Jan 6 of the surrounding period.
# For 1992 Jan 1, the window is Dec 27, 1991 to Jan 6, 1992.
# For 2002 Jan 1, the window is Dec 27, 2001 to Jan 6, 2002.
# So dates like Dec 27, 1991 (in the extension) would be included in the window of Jan 1, 1992.

# So the pool for doy d is all dates D such that there exists a baseline date B (1992-01-01 to 2002-12-31)
# with doy(B) = d and |D - B| <= 5 calendar days.

# Let me implement this efficiently.

# First, identify which baseline dates are in 1992-01-01 to 2002-12-31
base_mask_1992_2002 = (base_dates >= pd.Timestamp('1992-01-01')) & (base_dates <= pd.Timestamp('2002-12-31'))
print(f"Dates in 1992-2002: {base_mask_1992_2002.sum()}")

# For each doy d, find all baseline dates in 1992-2002 with that doy
# Then find all dates in our full range within ±5 calendar days of those dates

from collections import defaultdict

# Build pools
pools = {}  # doy -> list of indices in base_dates
for d in range(1, 367):
    if d == 60:
        continue
    # Find baseline dates in 1992-2002 with doy d
    mask = base_mask_1992_2002 & (base_doy == d)
    baseline_dates_with_doy = base_dates[mask]
    
    if len(baseline_dates_with_doy) == 0:
        print(f"doy {d}: no baseline dates in 1992-2002")
        pools[d] = np.array([], dtype=int)
        continue
    
    # Find all dates in our full range within ±5 calendar days
    pool_mask = np.zeros(len(base_dates), dtype=bool)
    for bd in baseline_dates_with_doy:
        start = bd - pd.Timedelta(days=5)
        end = bd + pd.Timedelta(days=5)
        pool_mask |= (base_dates >= start) & (base_dates <= end)
    
    pools[d] = np.where(pool_mask)[0]
    print(f"doy {d}: {len(pools[d])} dates in pool")

print("\nDone building pools")
