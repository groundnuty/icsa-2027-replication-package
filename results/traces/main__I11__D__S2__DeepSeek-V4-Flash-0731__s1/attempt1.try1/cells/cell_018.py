
import numpy as np
from datetime import date
from collections import defaultdict
import xarray as xr
import pandas as pd

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))

target = region.sel(time=slice('2021-06-01', '2021-08-31'))
target_sst = target.analysed_sst.values.astype(np.float64)
target_dates = pd.to_datetime(target.time.values).date

baseline_ext = region.sel(time=slice('1991-12-27', '2003-01-05'))
baseline_sst = baseline_ext.analysed_sst.values.astype(np.float64)
baseline_dates = pd.to_datetime(baseline_ext.time.values).date

sea_mask = np.all(np.isfinite(target_sst), axis=0)
n_sea = sea_mask.sum()
print("Sea cells:", n_sea)

# Day of year
CUM = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_from_md(month, day):
    return CUM[month-1] + day

def get_doy(d):
    return doy_from_md(d.month, d.day)

# Build pools
baseline_mask = np.array([(date(1992,1,1) <= d <= date(2002,12,31)) for d in baseline_dates])
baseline_idx = np.where(baseline_mask)[0]

pool_indices = defaultdict(list)
for bi in baseline_idx:
    b = baseline_dates[bi]
    b_doy = get_doy(b)
    if b_doy == 60:
        continue
    lo = max(0, bi - 5)
    hi = min(len(baseline_dates)-1, bi + 5)
    pool_indices[b_doy].extend(list(range(lo, hi+1)))

# Compute threshold and climatology for each day-of-year pool, vectorized
threshold = np.zeros((366, 60, 60), dtype=np.float64)
climatology = np.zeros((366, 60, 60), dtype=np.float64)

# Extract sea cell SST values for each pool and compute statistics
# For efficiency, reshape to (n_dates, 3600) and operate on sea cells
sea_flat = sea_mask.flatten()
sea_pos = np.where(sea_flat)[0]

for d in range(1, 367):
    if d == 60:
        continue
    idx = pool_indices.get(d, [])
    if not idx:
        continue
    idx = np.array(idx)
    sst_sub = baseline_sst[idx]  # (n_dates, 60, 60)
    sst_flat = sst_sub.reshape(len(idx), -1)  # (n_dates, 3600)
    sst_sea = sst_flat[:, sea_pos]  # (n_dates, n_sea)
    # Compute nanpercentile and nanmean along axis 0
    pct = np.nanpercentile(sst_sea, 90, axis=0, method='hazen')
    mean = np.nanmean(sst_sea, axis=0)
    # Store back
    threshold[d-1].flat[sea_pos] = pct
    climatology[d-1].flat[sea_pos] = mean

print("Computed thresholds and climatology for all pools")

# Set day 60 as mean of days 59 and 61
threshold[59] = (threshold[58] + threshold[60]) / 2.0
climatology[59] = (climatology[58] + climatology[60]) / 2.0

# Smooth with 31-day centered moving mean wrapping around year
def smooth_wrap(arr):
    # arr: (366, 60, 60), returns smoothed version
    result = np.zeros_like(arr)
    # For each day index i (0-365), average days i-15 to i+15 (mod 366)
    for i in range(366):
        indices = [(i + offset) % 366 for offset in range(-15, 16)]
        result[i] = np.mean(arr[indices], axis=0)
    return result

threshold_smooth = smooth_wrap(threshold)
climatology_smooth = smooth_wrap(climatology)

print("Smoothed thresholds and climatology")

# Save intermediate results for later use
np.save('/work/threshold_smooth.npy', threshold_smooth)
np.save('/work/climatology_smooth.npy', climatology_smooth)
np.save('/work/sea_mask.npy', sea_mask)
print("Saved intermediate results")
