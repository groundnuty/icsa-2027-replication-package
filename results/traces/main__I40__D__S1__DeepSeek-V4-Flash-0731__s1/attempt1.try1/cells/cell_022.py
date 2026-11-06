
import numpy as np
import pandas as pd
from datetime import date, timedelta

base_times = np.load('/work/base_times.npy')
base_dates = pd.DatetimeIndex(base_times)

def date_to_doy(dt):
    year, month, day = dt.year, dt.month, dt.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[m] for m in range(0, month-1)) + day
    return doy

base_doy = np.array([date_to_doy(d) for d in base_dates])

# Check pool for doy 1 (Jan 1)
mask_92_02 = (base_dates >= pd.Timestamp('1992-01-01')) & (base_dates <= pd.Timestamp('2002-12-31'))
mask_doy1 = mask_92_02 & (base_doy == 1)
dates_doy1 = base_dates[mask_doy1]
print(f"Baseline dates with doy 1: {len(dates_doy1)}")
for d in dates_doy1:
    print(f"  {d}")

# The first baseline date with doy 1 is Jan 1, 1992
# Its window is Dec 27, 1991 to Jan 6, 1992
# Do we have Dec 27-31, 1991 in our data?
print(f"\nOur data starts at: {base_dates[0]}")
print(f"Our data ends at: {base_dates[-1]}")

# Check if Dec 27-31, 1991 dates are in the pool
pool_mask = np.zeros(len(base_dates), dtype=bool)
for bd in dates_doy1:
    start = bd - pd.Timedelta(days=5)
    end = bd + pd.Timedelta(days=5)
    pool_mask |= (base_dates >= start) & (base_dates <= end)

pool_dates = base_dates[pool_mask]
print(f"\nPool for doy 1: {len(pool_dates)} dates")
dec91 = pool_dates[(pool_dates.year == 1991) & (pool_dates.month == 12)]
print(f"Dec 1991 dates in pool: {dec91}")
