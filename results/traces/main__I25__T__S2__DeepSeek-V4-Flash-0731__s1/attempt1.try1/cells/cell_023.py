
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict
import fsspec
import xarray as xr
import os
import json

def day_of_year(dt):
    cum_days_leap = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days_leap[dt.month - 1] + dt.day

# =====================
# Load data
# =====================
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    lat_idx = np.where((ds.latitude.values >= 57.57) & (ds.latitude.values <= 58.77))[0]
    lon_idx = np.where((ds.longitude.values >= 10.25) & (ds.longitude.values <= 11.45))[0]
    
    # Baseline data (1991-12-27 to 2003-01-05)
    b_start = np.datetime64('1991-12-27')
    b_end = np.datetime64('2003-01-05')
    time_vals = ds.time.values
    b_mask = (time_vals >= b_start) & (time_vals <= b_end)
    b_idx = np.where(b_mask)[0]
    
    baseline_sst = ds['analysed_sst'].isel(
        time=b_idx, latitude=lat_idx, longitude=lon_idx
    ).values
    baseline_time = time_vals[b_idx]
    
    # Target data (2016-06-01 to 2016-08-31)
    t_start = np.datetime64('2016-06-01')
    t_end = np.datetime64('2016-08-31')
    t_mask = (time_vals >= t_start) & (time_vals <= t_end)
    t_idx = np.where(t_mask)[0]
    
    target_sst = ds['analysed_sst'].isel(
        time=t_idx, latitude=lat_idx, longitude=lon_idx
    ).values
    target_time = time_vals[t_idx]
    
    lat_values = ds.latitude.values[lat_idx]
    lon_values = ds.longitude.values[lon_idx]

baseline_dt = [pd.Timestamp(t).to_pydatetime() for t in baseline_time]
target_dt = [pd.Timestamp(t).to_pydatetime() for t in target_time]

print(f"Baseline: {len(baseline_dt)} dates, {baseline_dt[0]} to {baseline_dt[-1]}")
print(f"Target: {len(target_dt)} dates, {target_dt[0]} to {target_dt[-1]}")

# =====================
# Build pool indices
# =====================
start = datetime(1991, 12, 27)
end = datetime(2003, 1, 5)
all_loaded_dates = []
d = start
while d <= end:
    all_loaded_dates.append(d)
    d += timedelta(days=1)

date_to_idx = {dt: i for i, dt in enumerate(all_loaded_dates)}

pool_indices = defaultdict(set)
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

d = baseline_start
while d <= baseline_end:
    doy = day_of_year(d)
    if doy != 60:
        for offset in range(-5, 6):
            x = d + timedelta(days=offset)
            if x in date_to_idx:
                pool_indices[doy].add(date_to_idx[x])
    d += timedelta(days=1)

pool_indices = {doy: sorted(list(indices)) for doy, indices in pool_indices.items()}

# =====================
# Identify sea cells
# =====================
sea_mask = np.all(np.isfinite(target_sst), axis=0)  # (lat, lon)
n_sea = sea_mask.sum()
print(f"Sea cells: {n_sea}")

# Flatten target and baseline to sea cells only
target_sst_sea = target_sst[:, sea_mask]  # (92, n_sea)
baseline_sst_sea = baseline_sst[:, sea_mask]  # (n_baseline, n_sea)

# =====================
# Compute threshold and climatology for each day of year
# =====================
print("Computing thresholds and climatologies...")
threshold = np.full((366, n_sea), np.nan, dtype=np.float64)
climatology = np.full((366, n_sea), np.nan, dtype=np.float64)

for doy, idx_list in pool_indices.items():
    pool = baseline_sst_sea[idx_list, :].astype(np.float64)
    threshold[doy-1, :] = np.nanpercentile(pool, 90, axis=0, method='hazen')
    climatology[doy-1, :] = np.nanmean(pool, axis=0)

# Set day 60 (index 59) to mean of days 59 (index 58) and 61 (index 60)
threshold[59, :] = (threshold[58, :] + threshold[60, :]) / 2.0
climatology[59, :] = (climatology[58, :] + climatology[60, :]) / 2.0

print(f"Threshold shape: {threshold.shape}, NaN count: {np.isnan(threshold).sum()}")
print(f"Climatology shape: {climatology.shape}, NaN count: {np.isnan(climatology).sum()}")

# =====================
# Smooth with 31-day centred moving mean that wraps
# =====================
print("Smoothing...")
def smooth_wrap(data, window=31):
    n = data.shape[0]
    half = window // 2  # 15
    result = np.empty_like(data)
    # Precompute the wrap indices for efficiency
    for i in range(n):
        idx = [(i + j) % n for j in range(-half, half + 1)]
        result[i] = np.mean(data[idx], axis=0)
    return result

threshold_smoothed = smooth_wrap(threshold)
climatology_smoothed = smooth_wrap(climatology)
print("Smoothing complete")

# Save intermediate results
os.makedirs('output', exist_ok=True)
np.save('output/threshold_smoothed.npy', threshold_smoothed)
np.save('output/climatology_smoothed.npy', climatology_smoothed)
np.save('output/sea_mask.npy', sea_mask)
np.save('output/target_sst_sea.npy', target_sst_sea)
np.save('output/target_sst_full.npy', target_sst)
np.save('output/target_time.npy', target_time)
np.save('output/lat_values.npy', lat_values)
np.save('output/lon_values.npy', lon_values)

# Save day_of_year for target dates
target_doy = np.array([day_of_year(dt) for dt in target_dt])
np.save('output/target_doy.npy', target_doy)

print("Intermediate results saved")
