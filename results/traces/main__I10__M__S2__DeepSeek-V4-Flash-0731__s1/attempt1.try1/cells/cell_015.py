
import numpy as np
from datetime import date, timedelta
from collections import defaultdict
import xarray as xr
import pandas as pd
import json
import os

# Reload data
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
lat = ds['latitude'].values
lon = ds['longitude'].values
time = ds['time'].values
time_dates = pd.to_datetime(time).date

lat_mask = (lat >= 55.67) & (lat <= 56.87)
lon_mask = (lon >= 16.45) & (lon <= 17.65)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]

pool_start = date(1991, 12, 27)
pool_end = date(2003, 1, 5)
target_start = date(2005, 6, 1)
target_end = date(2005, 8, 31)

pool_mask = (time_dates >= pool_start) & (time_dates <= pool_end)
target_mask = (time_dates >= target_start) & (time_dates <= target_end)
time_idx = np.where(pool_mask | target_mask)[0]

sst = ds['analysed_sst'].isel(time=time_idx, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

pool_local = np.where(pool_mask[time_idx])[0]
target_local = np.where(target_mask[time_idx])[0]

# Sea cells
target_sst = sst[target_local]
sea_cells = np.all(np.isfinite(target_sst), axis=0)
print("Sea cells:", sea_cells.sum(), "of", sea_cells.size)

# Day of year mapping
def doy_map(d):
    months = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(months[:d.month-1]) + d.day

# Build pools
baseline_dates_set = set()
d = date(1992, 1, 1)
while d <= date(2002, 12, 31):
    baseline_dates_set.add(d)
    d += timedelta(days=1)

pool_dates_actual = []
d = date(1991, 12, 27)
while d <= date(2003, 1, 5):
    pool_dates_actual.append(d)
    d += timedelta(days=1)

doy_to_pool_idx = defaultdict(list)
for pi, t in enumerate(pool_dates_actual):
    for offset in range(-5, 6):
        b = t + timedelta(days=offset)
        if b in baseline_dates_set:
            dd = doy_map(b)
            if dd != 60:
                doy_to_pool_idx[dd].append(pi)

doy_to_pool_idx_arr = {d: np.array(idx) for d, idx in doy_to_pool_idx.items()}

# Compute thresholds and climatology
n_doy = 366
n_lat, n_lon = 60, 60
pool_sst = sst[pool_local]

thresholds = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)

for d in range(1, n_doy + 1):
    if d == 60:
        continue
    idx = doy_to_pool_idx_arr[d]
    if len(idx) == 0:
        continue
    pool_data = pool_sst[idx]
    
    valid = np.isfinite(pool_data) & sea_cells[None, :, :]
    counts = valid.sum(axis=0)
    
    sums = np.where(valid, pool_data, 0.0).sum(axis=0)
    climatology[d-1] = np.where(counts > 0, sums / np.maximum(counts, 1), np.nan)
    
    valid_cells = sea_cells & (counts > 0)
    for ci in range(n_lat):
        for cj in range(n_lon):
            if valid_cells[ci, cj]:
                vals = pool_data[:, ci, cj]
                vals_valid = vals[valid[:, ci, cj]]
                thresholds[d-1, ci, cj] = np.percentile(vals_valid, 90, method='hazen')

# Set day 60
thresholds[59] = (thresholds[58] + thresholds[60]) / 2.0
climatology[59] = (climatology[58] + climatology[60]) / 2.0

# Check which cells have all-NaN in thresholds (should only be non-sea cells)
all_nan_thresh = np.all(np.isnan(thresholds), axis=0)
print("Cells with all-NaN thresholds:", all_nan_thresh.sum())
print("These should all be non-sea cells:", np.all(all_nan_thresh == ~sea_cells))

# Check sea cells have finite thresholds everywhere
sea_nan_thresh = np.isnan(thresholds[:, sea_cells])
print("NaN thresholds among sea cells:", sea_nan_thresh.sum(), "of", sea_nan_thresh.size)

# Smoothing
def smooth_wrap(arr):
    n = 366
    result = np.zeros_like(arr)
    for d in range(n):
        indices = [(d + k) % n for k in range(-15, 16)]
        # Use manual mean to handle all-NaN without warnings
        window = arr[indices]
        valid = np.isfinite(window)
        counts = valid.sum(axis=0)
        sums = np.where(valid, window, 0.0).sum(axis=0)
        result[d] = np.where(counts > 0, sums / np.maximum(counts, 1), np.nan)
    return result

thresholds_smooth = smooth_wrap(thresholds)
climatology_smooth = smooth_wrap(climatology)

# Check NaN in smoothed values for sea cells
sea_nan_thresh_s = np.isnan(thresholds_smooth[:, sea_cells])
print("NaN smoothed thresholds among sea cells:", sea_nan_thresh_s.sum(), "of", sea_nan_thresh_s.size)

sea_nan_clim_s = np.isnan(climatology_smooth[:, sea_cells])
print("NaN smoothed climatology among sea cells:", sea_nan_clim_s.sum(), "of", sea_nan_clim_s.size)

# Check a sample sea cell
sea_idx = np.argwhere(sea_cells)
si, sj = sea_idx[0]
print(f"\nSample sea cell ({si},{sj}):")
print("Thresholds doy 1-5:", thresholds_smooth[0:5, si, sj])
print("Climatology doy 1-5:", climatology_smooth[0:5, si, sj])
print("Thresholds doy 59-63:", thresholds_smooth[58:63, si, sj])
print("Climatology doy 59-63:", climatology_smooth[58:63, si, sj])
print("Thresholds doy 360-366:", thresholds_smooth[359:366, si, sj])
print("Climatology doy 360-366:", climatology_smooth[359:366, si, sj])
