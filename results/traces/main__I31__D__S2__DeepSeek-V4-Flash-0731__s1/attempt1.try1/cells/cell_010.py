
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

# Sea cells mask
target_values = target_data.values
sea_cells = np.all(np.isfinite(target_values), axis=0)  # (60, 60)

# Build pool masks for each day of year
print("Building pool masks...")
pool_masks = {}
for d in range(1, 367):
    if d == 60:
        continue
    baseline_indices = np.where(in_baseline & (base_doy == d))[0]
    pool_mask = np.zeros(len(base_times), dtype=bool)
    for bi in baseline_indices:
        lo = max(0, bi - 5)
        hi = min(len(base_times) - 1, bi + 5)
        pool_mask[lo:hi+1] = True
    pool_masks[d] = pool_mask
    #print(f"Day {d}: {pool_mask.sum()} pool entries")

print("Pool masks built for", len(pool_masks), "days of year")

# Check: how many baseline dates for day 60?
print("Baseline dates with doy=60:", np.where(in_baseline & (base_doy == 60))[0])
# Day 60 should have no pool of its own (it's Feb 29 in leap years)
# But Feb 29 values belong to the windows of their calendar neighbors

# Let's verify: day 59 should include Feb 29 values in its window
# Day 59 = Feb 28. Baseline dates with doy=59: Feb 28 in non-leap years.
# Window: Feb 23 to Mar 5. This includes Feb 29 in leap years.

# For day 60 (Feb 29), there's no pool. We set threshold and climatology to mean of days 59 and 61.
# But wait - in leap years, Feb 29 has doy=60. In non-leap years, there's no day 60.
# The baseline period 1992-2002 includes leap years 1992, 1996, 2000.
# In those years, Feb 29 has doy=60.
# But day 60 gets no pool of its own, and its threshold/climatology is set to mean of days 59 and 61.

print("\nChecking day 59 pool...")
print("Baseline dates with doy=59:", base_times[np.where(in_baseline & (base_doy == 59))[0]])
print("Pool size:", pool_masks[59].sum())
