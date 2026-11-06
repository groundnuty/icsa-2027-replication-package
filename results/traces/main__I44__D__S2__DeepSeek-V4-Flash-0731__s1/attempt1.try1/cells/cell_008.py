
import xarray as xr
import numpy as np
import pandas as pd

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Define day_of_year function
def doy(month, day):
    offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return offsets[month-1] + day

def date_to_doy(dt):
    return doy(dt.month, dt.day)

# Baseline period
baseline_start = pd.Timestamp('1992-01-01')
baseline_end = pd.Timestamp('2002-12-31')
baseline_dates = pd.date_range(baseline_start, baseline_end, freq='D')

# Extended data period
data_start = pd.Timestamp('1991-12-27')
data_end = pd.Timestamp('2003-01-05')
data_dates = pd.date_range(data_start, data_end, freq='D')

# Build mapping: date -> doy
date_doy_map = {dt: date_to_doy(dt) for dt in data_dates}

# For each doy d (1-366, d != 60), find pool dates
pool_dates = {}  # d -> list of dates

for d in range(1, 367):
    if d == 60:
        continue
    
    # Find all baseline dates with doy = d
    base_dates_d = [dt for dt in baseline_dates if date_to_doy(dt) == d]
    
    # For each baseline date, expand ±5 days
    pool = set()
    for t0 in base_dates_d:
        for offset in range(-5, 6):
            t = t0 + pd.Timedelta(days=offset)
            if data_start <= t <= data_end:
                pool.add(t)
    
    pool_dates[d] = sorted(pool)

# Check a few
for d in [1, 59, 61, 90, 366]:
    dates = pool_dates[d]
    print(f"DOY {d}: {len(dates)} pool dates")
    print(f"  First 5: {[str(x.date()) for x in dates[:5]]}")
    print(f"  Last 5: {[str(x.date()) for x in dates[-5:]]}")

# Check day 60 handling
print(f"\nDay 60 pool dates: (no pool)")

# Check total pool sizes
total = sum(len(v) for v in pool_dates.values())
print(f"Total pool dates across all doys: {total}")
print(f"Unique dates in extended period: {len(data_dates)}")
