
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
from collections import defaultdict
import fsspec
import xarray as xr

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
    
    # Baseline data
    b_start = np.datetime64('1991-12-27')
    b_end = np.datetime64('2003-01-05')
    time_vals = ds.time.values
    b_mask = (time_vals >= b_start) & (time_vals <= b_end)
    b_idx = np.where(b_mask)[0]
    
    baseline_sst = ds['analysed_sst'].isel(
        time=b_idx, latitude=lat_idx, longitude=lon_idx
    ).values
    baseline_time = time_vals[b_idx]
    
    # Target data
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
print(f"Baseline SST shape: {baseline_sst.shape}")
print(f"Target SST shape: {target_sst.shape}")

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
print(f"Sea cells: {sea_mask.sum()}")

# Flatten to sea-cell only arrays
# target_sst: (92, 60, 60), sea_mask: (60, 60)
n_lat, n_lon = sea_mask.shape
sea_flat = sea_mask.flatten()
n_sea = sea_flat.sum()

# Target SST for sea cells: (92, n_sea)
target_sst_sea = target_sst[:, sea_mask]
print(f"Target SST (sea cells): {target_sst_sea.shape}")

# Baseline SST for sea cells: (n_baseline, n_sea)
baseline_sst_sea = baseline_sst[:, sea_mask]
print(f"Baseline SST (sea cells): {baseline_sst_sea.shape}")

# =====================
# Compute threshold and climatology
# =====================
# For each day d (1-366, d≠60), compute threshold and climatology for each sea cell
threshold = np.full((366, n_sea), np.nan, dtype=np.float64)
climatology = np.full((366, n_sea), np.nan, dtype=np.float64)

for doy, idx_list in pool_indices.items():
    # Get pool values for this day: (len(idx_list), n_sea)
    pool = baseline_sst_sea[idx_list, :].astype(np.float64)
    # Compute 90th percentile ignoring NaN (method='hazen')
    threshold[doy-1, :] = np.nanpercentile(pool, 90, axis=0, method='hazen')
    # Compute mean ignoring NaN
    climatology[doy-1, :] = np.nanmean(pool, axis=0)

print("Threshold computed for all days with pools")
print(f"Threshold shape: {threshold.shape}")

# Set day 60 to mean of days 59 and 61
threshold[59, :] = (threshold[58, :] + threshold[60, :]) / 2.0
climatology[59, :] = (climatology[58, :] + climatology[60, :]) / 2.0

# Check for NaN in threshold/climatology
print(f"NaN in threshold: {np.isnan(threshold).sum()}")
print(f"NaN in climatology: {np.isnan(climatology).sum()}")
