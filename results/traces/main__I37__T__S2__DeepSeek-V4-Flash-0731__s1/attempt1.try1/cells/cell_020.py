
import pandas as pd
import numpy as np
import fsspec
import xarray as xr
import json
import os

os.makedirs('output', exist_ok=True)

fs = fsspec.filesystem('onedata')
data_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

# ====== Parameters ======
LAT_MIN, LAT_MAX = 60.09, 61.29
LON_MIN, LON_MAX = 20.01, 21.21

# ====== Fixed day-of-year mapping ======
def fixed_doy(ts):
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[ts.month - 1] + ts.day

# ====== Load dataset ======
with fs.open(data_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    lat = ds.latitude.values
    lon = ds.longitude.values
    time_vals = ds.time.values
    all_dates = pd.to_datetime(time_vals)
    
    # Region indices
    lat_idx = np.where((lat >= LAT_MIN) & (lat <= LAT_MAX))[0]
    lon_idx = np.where((lon >= LON_MIN) & (lon <= LON_MAX))[0]
    
    # Time indices
    ext_start = pd.Timestamp('1991-12-27')
    ext_end = pd.Timestamp('2003-01-05')
    ext_time_idx = np.where((all_dates >= ext_start) & (all_dates <= ext_end))[0]
    
    tgt_start = pd.Timestamp('2012-06-01')
    tgt_end = pd.Timestamp('2012-08-31')
    tgt_time_idx = np.where((all_dates >= tgt_start) & (all_dates <= tgt_end))[0]
    
    # Load data (as float64 for double precision)
    baseline_sst = ds['analysed_sst'].isel(
        time=slice(int(ext_time_idx[0]), int(ext_time_idx[-1])+1),
        latitude=slice(int(lat_idx[0]), int(lat_idx[-1])+1),
        longitude=slice(int(lon_idx[0]), int(lon_idx[-1])+1)
    ).load().values.astype(np.float64)
    
    target_sst = ds['analysed_sst'].isel(
        time=slice(int(tgt_time_idx[0]), int(tgt_time_idx[-1])+1),
        latitude=slice(int(lat_idx[0]), int(lat_idx[-1])+1),
        longitude=slice(int(lon_idx[0]), int(lon_idx[-1])+1)
    ).load().values.astype(np.float64)
    
    region_lat = lat[lat_idx].copy()
    region_lon = lon[lon_idx].copy()
    target_dates = all_dates[tgt_time_idx].copy()
    ext_dates_arr = all_dates[ext_time_idx].copy()

print(f"Baseline shape: {baseline_sst.shape}")
print(f"Target shape: {target_sst.shape}")
print(f"Target dates: {target_dates[0]} to {target_dates[-1]}")
n_lat, n_lon = target_sst.shape[1], target_sst.shape[2]
print(f"Grid: {n_lat} x {n_lon}")

# ====== Sea cells ======
sea_cells = ~np.isnan(target_sst).any(axis=0)
print(f"Sea cells: {sea_cells.sum()} out of {n_lat*n_lon}")

# ====== Build pool time indices ======
ext_dates_pd = pd.date_range('1991-12-27', '2003-01-05', freq='D')
base_dates_pd = pd.date_range('1992-01-01', '2002-12-31', freq='D')
base_doy = np.array([fixed_doy(d) for d in base_dates_pd])

# Map extended dates to indices in baseline_sst
ext_date_to_idx = {d: i for i, d in enumerate(ext_dates_pd)}

pool_time_indices = {}  # doy -> list of indices into baseline_sst
for d in range(1, 367):
    if d == 60:
        continue
    b_mask = (base_doy == d)
    b_dates_for_d = base_dates_pd[b_mask]
    pool_date_set = set()
    for b in b_dates_for_d:
        for t in ext_dates_pd:
            if abs((t - b).days) <= 5:
                pool_date_set.add(t)
    pool_time_indices[d] = sorted([ext_date_to_idx[t] for t in pool_date_set])

print("Pool construction done")

# ====== Compute threshold and climatology for each sea cell and doy ======
# Arrays: (366, n_lat, n_lon)
threshold_raw = np.full((366, n_lat, n_lon), np.nan)
climatology_raw = np.full((366, n_lat, n_lon), np.nan)

# For each doy, we have a set of time indices. For each sea cell, compute stats.
for d in range(1, 367):
    if d == 60:
        continue
    pool_idx = np.array(pool_time_indices[d])
    # Extract pool values for all cells: (n_pool, n_lat, n_lon)
    pool_vals = baseline_sst[pool_idx]  # (121, 60, 60)
    
    # For sea cells, compute percentile and mean
    for i in range(n_lat):
        for j in range(n_lon):
            if not sea_cells[i, j]:
                continue
            vals = pool_vals[:, i, j]
            valid = vals[~np.isnan(vals)]
            if len(valid) > 0:
                threshold_raw[d-1, i, j] = np.percentile(valid, 90, method='hazen')
                climatology_raw[d-1, i, j] = np.mean(valid)

print("Threshold/climatology raw computed")

# Set day 60 to mean of days 59 and 61
threshold_raw[59] = (threshold_raw[58] + threshold_raw[60]) / 2
climatology_raw[59] = (climatology_raw[58] + climatology_raw[60]) / 2

print("Day 60 set")

# ====== Smoothing: 31-day centered moving mean wrapping around the year ======
# For each day d, average days d-15 to d+15 (modulo 366)
def smooth_wrap(arr):
    """Smooth 366-length array with 31-day centered moving mean wrapping around year.
    arr shape: (366, n_lat, n_lon)"""
    result = np.full_like(arr, np.nan)
    n_days = 366
    for d in range(n_days):
        idxs = [(d + k) % n_days for k in range(-15, 16)]
        result[d] = np.mean(arr[idxs], axis=0)
    return result

threshold_smooth = smooth_wrap(threshold_raw)
climatology_smooth = smooth_wrap(climatology_raw)

print("Smoothing done")
print(f"NaN in threshold_smooth: {np.isnan(threshold_smooth).sum()}")
print(f"NaN in climatology_smooth: {np.isnan(climatology_smooth).sum()}")
