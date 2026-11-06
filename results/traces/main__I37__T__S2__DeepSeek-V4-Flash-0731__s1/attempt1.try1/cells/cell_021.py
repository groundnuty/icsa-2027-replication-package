
import pandas as pd
import numpy as np
import json
import os

# Continue from the loaded data - need to reload
# Actually let me write the complete script from scratch with all steps

import fsspec
import xarray as xr

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
    
    lat_idx = np.where((lat >= LAT_MIN) & (lat <= LAT_MAX))[0]
    lon_idx = np.where((lon >= LON_MIN) & (lon <= LON_MAX))[0]
    
    ext_start = pd.Timestamp('1991-12-27')
    ext_end = pd.Timestamp('2003-01-05')
    ext_time_idx = np.where((all_dates >= ext_start) & (all_dates <= ext_end))[0]
    
    tgt_start = pd.Timestamp('2012-06-01')
    tgt_end = pd.Timestamp('2012-08-31')
    tgt_time_idx = np.where((all_dates >= tgt_start) & (all_dates <= tgt_end))[0]
    
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

n_lat, n_lon = target_sst.shape[1], target_sst.shape[2]

# ====== Sea cells ======
sea_cells = ~np.isnan(target_sst).any(axis=0)
print(f"Sea cells: {sea_cells.sum()} out of {n_lat*n_lon}")

# ====== Build pool time indices ======
ext_dates_pd = pd.date_range('1991-12-27', '2003-01-05', freq='D')
base_dates_pd = pd.date_range('1992-01-01', '2002-12-31', freq='D')
base_doy = np.array([fixed_doy(d) for d in base_dates_pd])

ext_date_to_idx = {d: i for i, d in enumerate(ext_dates_pd)}

pool_time_indices = {}
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

# ====== Compute threshold and climatology ======
threshold_raw = np.full((366, n_lat, n_lon), np.nan)
climatology_raw = np.full((366, n_lat, n_lon), np.nan)

for d in range(1, 367):
    if d == 60:
        continue
    pool_idx = np.array(pool_time_indices[d])
    pool_vals = baseline_sst[pool_idx]
    
    for i in range(n_lat):
        for j in range(n_lon):
            if not sea_cells[i, j]:
                continue
            vals = pool_vals[:, i, j]
            valid = vals[~np.isnan(vals)]
            if len(valid) > 0:
                threshold_raw[d-1, i, j] = np.percentile(valid, 90, method='hazen')
                climatology_raw[d-1, i, j] = np.mean(valid)

# Set day 60 to mean of days 59 and 61
threshold_raw[59] = (threshold_raw[58] + threshold_raw[60]) / 2
climatology_raw[59] = (climatology_raw[58] + climatology_raw[60]) / 2

# ====== Smoothing ======
def smooth_wrap(arr):
    result = np.full_like(arr, np.nan)
    n_days = 366
    for d in range(n_days):
        idxs = [(d + k) % n_days for k in range(-15, 16)]
        result[d] = np.mean(arr[idxs], axis=0)
    return result

threshold = smooth_wrap(threshold_raw)
climatology = smooth_wrap(climatology_raw)

print("Threshold and climatology computed and smoothed")

# ====== Per-cell MHWs in target period ======
# target_sst shape: (92, n_lat, n_lon)
# For each target day, compute its doy and get the corresponding threshold

n_target = len(target_dates)
target_doy = np.array([fixed_doy(d) for d in target_dates])
print(f"Target doys: {target_doy}")

# For each cell, determine hot days: SST >= threshold[doy-1, cell]
hot = np.zeros((n_target, n_lat, n_lon), dtype=bool)
for t in range(n_target):
    d = target_doy[t]
    thr = threshold[d-1]  # (n_lat, n_lon)
    hot[t] = (target_sst[t] >= thr) & sea_cells

print(f"Hot days count: {hot.sum()}")
print(f"Hot fraction: {hot.sum() / (n_target * sea_cells.sum())}")
