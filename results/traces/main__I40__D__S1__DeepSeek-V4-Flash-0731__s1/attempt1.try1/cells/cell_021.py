
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Load data
base_times = np.load('/work/base_times.npy')
base_dates = pd.DatetimeIndex(base_times)

def date_to_doy(dt):
    year, month, day = dt.year, dt.month, dt.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[m] for m in range(0, month-1)) + day
    return doy

base_doy = np.array([date_to_doy(d) for d in base_dates])

# Check which dates have doy 60 in baseline
doy60_dates = base_dates[base_doy == 60]
print(f"Dates with doy 60: {doy60_dates}")
for d in doy60_dates:
    print(f"  {d} -> doy {date_to_doy(d)}")

# Check pool for doy 59 (Feb 28)
mask_92_02 = (base_dates >= pd.Timestamp('1992-01-01')) & (base_dates <= pd.Timestamp('2002-12-31'))
mask_doy59 = mask_92_02 & (base_doy == 59)
dates_doy59 = base_dates[mask_doy59]
print(f"\nBaseline dates with doy 59: {len(dates_doy59)}")
for d in dates_doy59:
    print(f"  {d}")

# Build pool for doy 59
pool_mask = np.zeros(len(base_dates), dtype=bool)
for bd in dates_doy59:
    start = bd - pd.Timedelta(days=5)
    end = bd + pd.Timedelta(days=5)
    pool_mask |= (base_dates >= start) & (base_dates <= end)

pool_dates = base_dates[pool_mask]
# Check if any Feb 29 dates are in the pool
feb29_mask = (pool_dates.month == 2) & (pool_dates.day == 29)
print(f"\nPool for doy 59 has {len(pool_dates)} dates")
print(f"Feb 29 dates in pool: {pool_dates[feb29_mask]}")

# Check pool for doy 61 (Mar 1)
mask_doy61 = mask_92_02 & (base_doy == 61)
dates_doy61 = base_dates[mask_doy61]
print(f"\nBaseline dates with doy 61: {len(dates_doy61)}")

pool_mask61 = np.zeros(len(base_dates), dtype=bool)
for bd in dates_doy61:
    start = bd - pd.Timedelta(days=5)
    end = bd + pd.Timedelta(days=5)
    pool_mask61 |= (base_dates >= start) & (base_dates <= end)

pool_dates61 = base_dates[pool_mask61]
feb29_mask61 = (pool_dates61.month == 2) & (pool_dates61.day == 29)
print(f"Pool for doy 61 has {len(pool_dates61)} dates")
print(f"Feb 29 dates in pool 61: {pool_dates61[feb29_mask61]}")
