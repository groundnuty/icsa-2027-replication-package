
import numpy as np
import datetime
import pandas as pd

# Load data
baseline_sst = np.load('/work/baseline_sst.npy')  # (4028, 60, 60)
baseline_time_idx = np.load('/work/baseline_time_idx.npy')

import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time = ds.time.values
baseline_dates = time[baseline_time_idx]
baseline_dates_list = [pd.Timestamp(t).to_pydatetime().date() for t in baseline_dates]

# Day of year function
def doy_from_date(date):
    m = date.month
    d = date.day
    if m == 1:
        return d
    elif m == 2:
        return 31 + d
    elif m == 3:
        return 60 + d
    elif m == 4:
        return 91 + d
    elif m == 5:
        return 121 + d
    elif m == 6:
        return 152 + d
    elif m == 7:
        return 182 + d
    elif m == 8:
        return 213 + d
    elif m == 9:
        return 244 + d
    elif m == 10:
        return 274 + d
    elif m == 11:
        return 305 + d
    elif m == 12:
        return 335 + d
    return -1

# Build date_to_idx
date_to_idx = {}
for i, d in enumerate(baseline_dates_list):
    date_to_idx[d] = i

# Core baseline dates
baseline_core_start = datetime.date(1992, 1, 1)
baseline_core_end = datetime.date(2002, 12, 31)
core_dates = [d for d in baseline_dates_list if baseline_core_start <= d <= baseline_core_end]
core_doy = {d: doy_from_date(d) for d in core_dates}

# Build pools
pools = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    matching_dates = [d for d, dd in core_doy.items() if dd == doy]
    pool_dates = set()
    for t0 in matching_dates:
        for delta in range(-5, 6):
            t = t0 + datetime.timedelta(days=delta)
            if t in date_to_idx:
                pool_dates.add(t)
    pools[doy] = sorted(pool_dates)

# Now compute threshold and climatology for each day-of-year
# Convert baseline_sst to float64
baseline_sst64 = baseline_sst.astype(np.float64)

# For each day-of-year, collect all SST values in the pool per cell
# Shape: (doy_count, 60, 60)
n_lat, n_lon = 60, 60

# Pre-allocate
thresholds = np.full((366, n_lat, n_lon), np.nan)
climatologies = np.full((366, n_lat, n_lon), np.nan)

for doy in range(1, 367):
    if doy == 60:
        continue
    pool_dates = pools[doy]
    if not pool_dates:
        continue
    pool_indices = [date_to_idx[d] for d in pool_dates]
    
    # Extract SST values for these dates, per cell
    pool_sst = baseline_sst64[pool_indices, :, :]  # (n_dates, 60, 60)
    
    # Compute 90th percentile (method="hazen") and mean per cell
    # Ignoring NaN
    for i in range(n_lat):
        for j in range(n_lon):
            vals = pool_sst[:, i, j]
            valid = ~np.isnan(vals)
            if valid.any():
                v = vals[valid]
                thresholds[doy, i, j] = np.quantile(v, 0.9, method='hazen')
                climatologies[doy, i, j] = np.mean(v)
            else:
                thresholds[doy, i, j] = np.nan
                climatologies[doy, i, j] = np.nan

print(f"Threshold shape: {thresholds.shape}")
print(f"Climatology shape: {climatologies.shape}")

# Set day 60 as mean of days 59 and 61
thresholds[59, :, :] = (thresholds[58, :, :] + thresholds[60, :, :]) / 2
climatologies[59, :, :] = (climatologies[58, :, :] + climatologies[60, :, :]) / 2

# Check some values
print(f"\nDay 1 threshold sample: {thresholds[0, 0, 0]:.4f}")
print(f"Day 1 climatology sample: {climatologies[0, 0, 0]:.4f}")
print(f"Day 59 threshold sample: {thresholds[58, 0, 0]:.4f}")
print(f"Day 60 threshold sample: {thresholds[59, 0, 0]:.4f}")
print(f"Day 61 threshold sample: {thresholds[60, 0, 0]:.4f}")

# Save for later
np.save('/work/thresholds_raw.npy', thresholds)
np.save('/work/climatologies_raw.npy', climatologies)
print("\nSaved raw thresholds and climatologies.")
