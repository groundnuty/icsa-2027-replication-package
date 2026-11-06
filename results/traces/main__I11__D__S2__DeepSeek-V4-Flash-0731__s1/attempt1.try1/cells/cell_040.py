
import numpy as np
from datetime import date, timedelta
import xarray as xr
import pandas as pd
from collections import defaultdict

# Verify threshold computation for a specific cell and pool
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))

baseline_ext = region.sel(time=slice('1991-12-27', '2003-01-05'))
baseline_sst = baseline_ext.analysed_sst.values.astype(np.float64)
baseline_dates = pd.to_datetime(baseline_ext.time.values).date

CUM = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_from_md(month, day):
    return CUM[month-1] + day

def get_doy(d):
    return doy_from_md(d.month, d.day)

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

# For cell (0,0), day of year 153 (Jun 1)
# Get all SST values for this cell from the pool
cell_i, cell_j = 0, 0
pool153 = pool_indices.get(153, [])
sst_vals = baseline_sst[pool153, cell_i, cell_j]
sst_vals = sst_vals[np.isfinite(sst_vals)]
print(f"Cell (0,0), pool 153: {len(sst_vals)} finite values")
print(f"  Min: {np.min(sst_vals):.4f}, Max: {np.max(sst_vals):.4f}")
print(f"  Mean: {np.mean(sst_vals):.4f}")
print(f"  P90 (hazen): {np.percentile(sst_vals, 90, method='hazen'):.4f}")

# Verify against numpy
p90 = np.percentile(sst_vals, 90, method='hazen')
mean = np.mean(sst_vals)
print(f"\nExpected threshold (P90): {p90:.4f}")
print(f"Expected climatology (mean): {mean:.4f}")

# Load computed threshold
threshold_smooth = np.load('/work/threshold_smooth.npy')
climatology_smooth = np.load('/work/climatology_smooth.npy')

print(f"\nComputed threshold[152] (doy 153): {threshold_smooth[152, cell_i, cell_j]:.4f}")
print(f"Computed climatology[152] (doy 153): {climatology_smooth[152, cell_i, cell_j]:.4f}")

# The smoothed value should differ from the raw P90/mean
# Let me verify the smoothing is applied correctly
# For doy 153, the smoothed value is the mean of doy 138-168
# This would differ from the raw value
print("\nNote: Smoothed values differ from raw due to 31-day moving mean")
