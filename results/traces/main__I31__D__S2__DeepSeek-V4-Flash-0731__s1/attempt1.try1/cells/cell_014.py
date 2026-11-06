
import xarray as xr
import numpy as np
import pandas as pd
import datetime
import os

# Load data
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Load data
base_data = ds['analysed_sst'].isel(time=slice(3647, 7675), latitude=slice(260, 320), longitude=slice(485, 545)).load()
target_data = ds['analysed_sst'].isel(time=slice(12935, 13027), latitude=slice(260, 320), longitude=slice(485, 545)).load()

base_times = base_data.time.values
target_times = target_data.time.values

# Convert to float64
base_data64 = base_data.values.astype(np.float64)
target_data64 = target_data.values.astype(np.float64)

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

# Identify baseline dates
base_start = np.datetime64('1992-01-01')
base_end = np.datetime64('2002-12-31')
in_baseline = (base_times >= base_start) & (base_times <= base_end)

# Sea cells
sea_cells = np.all(np.isfinite(target_data64), axis=0)  # (60, 60)

# Build pool masks for each day of year
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

# Compute thresholds and climatology
thresholds = np.zeros((366, 60, 60), dtype=np.float64)
climatology = np.zeros((366, 60, 60), dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    mask = pool_masks[d]
    pool = base_data64[mask, :, :]  # (n_pool, 60, 60)
    
    with np.errstate(all='ignore'):
        p90 = np.nanpercentile(pool, 90, axis=0, method='hazen')
        mean_val = np.nanmean(pool, axis=0)
    
    thresholds[d-1, :, :] = p90
    climatology[d-1, :, :] = mean_val

# Day 60: mean of days 59 and 61
thresholds[59, :, :] = (thresholds[58, :, :] + thresholds[60, :, :]) / 2.0
climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2.0

# Smoothing: 31-day centered moving mean wrapping around the year
def smooth_wrap(arr):
    result = np.zeros_like(arr)
    for d in range(366):
        indices = [(d - 15 + i) % 366 for i in range(31)]
        result[d] = np.mean(arr[indices], axis=0)
    return result

thresholds_smooth = smooth_wrap(thresholds)
climatology_smooth = smooth_wrap(climatology)

print("Thresholds/climatology computed and smoothed")
print("Threshold shape:", thresholds_smooth.shape)
print("Climatology shape:", climatology_smooth.shape)

# Save intermediate results
np.save('/work/thresholds_smooth.npy', thresholds_smooth)
np.save('/work/climatology_smooth.npy', climatology_smooth)
np.save('/work/sea_cells.npy', sea_cells)
np.save('/work/base_doy.npy', base_doy)
np.save('/work/in_baseline.npy', in_baseline)
np.save('/work/base_times.npy', base_times)
np.save('/work/target_times.npy', target_times)
print("Saved intermediate results")
