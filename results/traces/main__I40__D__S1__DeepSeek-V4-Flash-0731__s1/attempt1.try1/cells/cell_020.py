
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Load data
baseline_sst = np.load('/work/baseline_sst.npy')
base_times = np.load('/work/base_times.npy')
base_dates = pd.DatetimeIndex(base_times)

# Day of year mapping
def date_to_doy(dt):
    year, month, day = dt.year, dt.month, dt.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[m] for m in range(0, month-1)) + day
    return doy

base_doy = np.array([date_to_doy(d) for d in base_dates])

# Verify pool for doy 153 (June 1)
# Baseline dates in 1992-2002 with doy 153: June 1 of each year 1992-2002
mask = (base_dates >= pd.Timestamp('1992-01-01')) & (base_dates <= pd.Timestamp('2002-12-31')) & (base_doy == 153)
dates_doy153 = base_dates[mask]
print(f"Baseline dates with doy 153: {len(dates_doy153)}")
for d in dates_doy153:
    print(f"  {d}")

# For each such date, the pool includes dates within ±5 calendar days
# So for June 1, 1992, the pool includes May 27 - June 6, 1992
# etc.

# Let me verify: the pool for doy 153 should include all dates in the range
# May 27 to June 6 for each year 1992-2002
# That's 11 * 11 = 121 dates

# Let me check if the pool construction matches
pool_mask = np.zeros(len(base_dates), dtype=bool)
for bd in dates_doy153:
    start = bd - pd.Timedelta(days=5)
    end = bd + pd.Timedelta(days=5)
    pool_mask |= (base_dates >= start) & (base_dates <= end)

pool_dates = base_dates[pool_mask]
print(f"\nPool for doy 153: {len(pool_dates)} dates")
print(f"First 15 pool dates: {pool_dates[:15]}")
print(f"Last 15 pool dates: {pool_dates[-15:]}")
