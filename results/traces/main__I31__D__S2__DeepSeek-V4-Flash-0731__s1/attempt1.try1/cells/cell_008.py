
import xarray as xr
import numpy as np
import pandas as pd
import datetime

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Load data
base_data = ds['analysed_sst'].isel(time=slice(3647, 7675), latitude=slice(260, 320), longitude=slice(485, 545)).load()
target_data = ds['analysed_sst'].isel(time=slice(12935, 13027), latitude=slice(260, 320), longitude=slice(485, 545)).load()

base_times = base_data.time.values
target_times = target_data.time.values

def doy_from_datetime64(t):
    dt = pd.Timestamp(t).to_pydatetime()
    year = dt.year
    month = dt.month
    day = dt.day
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if is_leap:
        days_in_month[1] = 29
    std_doy = sum(days_in_month[:month-1]) + day
    if not is_leap and month >= 3:
        return std_doy + 1
    else:
        return std_doy

base_doy = np.array([doy_from_datetime64(t) for t in base_times])

# Identify baseline dates (1992-01-01 to 2002-12-31)
base_start = np.datetime64('1992-01-01')
base_end = np.datetime64('2002-12-31')
in_baseline = (base_times >= base_start) & (base_times <= base_end)
print("Number of dates in baseline:", in_baseline.sum())

# For each day of year d (1-366), find baseline indices where doy == d
# Then for each such baseline date, find all dates within ±5 days
# Build a mask over the full extended baseline time axis

# First, let's create a pool mask for a single day of year to test
# Day 1: baseline dates with doy == 1, then ±5 day windows
d = 1
baseline_indices = np.where(in_baseline & (base_doy == d))[0]
print(f"Day {d}: {len(baseline_indices)} baseline dates")
print("Baseline dates:", base_times[baseline_indices])

# For each baseline date, find all dates within ±5 calendar days
pool_mask = np.zeros(len(base_times), dtype=bool)
for bi in baseline_indices:
    # dates within ±5 days
    lo = max(0, bi - 5)
    hi = min(len(base_times) - 1, bi + 5)
    pool_mask[lo:hi+1] = True

print(f"Pool size for day {d}: {pool_mask.sum()}")
