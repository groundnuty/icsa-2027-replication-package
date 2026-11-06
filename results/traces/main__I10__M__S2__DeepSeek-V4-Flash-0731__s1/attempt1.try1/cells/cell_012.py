
import numpy as np
from datetime import date, timedelta
from collections import defaultdict

# Reload data
import xarray as xr
import pandas as pd

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

# Day of year mapping
def doy_map(d):
    months = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(months[:d.month-1]) + d.day

# Baseline dates
baseline_dates_set = set()
d = date(1992, 1, 1)
while d <= date(2002, 12, 31):
    baseline_dates_set.add(d)
    d += timedelta(days=1)

# Pool dates
pool_dates_actual = []
d = date(1991, 12, 27)
while d <= date(2003, 1, 5):
    pool_dates_actual.append(d)
    d += timedelta(days=1)

# Build doy -> pool date indices
doy_to_pool_idx = defaultdict(list)
for pi, t in enumerate(pool_dates_actual):
    for offset in range(-5, 6):
        b = t + timedelta(days=offset)
        if b in baseline_dates_set:
            dd = doy_map(b)
            if dd != 60:
                doy_to_pool_idx[dd].append(pi)

# Convert to arrays
doy_to_pool_idx_arr = {}
for d, idx in doy_to_pool_idx.items():
    doy_to_pool_idx_arr[d] = np.array(idx)

# Vectorized computation
n_doy = 366
n_cells_lat, n_cells_lon = 60, 60
pool_sst = sst[pool_local]  # (4028, 60, 60)

thresholds = np.full((n_doy, n_cells_lat, n_cells_lon), np.nan, dtype=np.float64)
climatology = np.full((n_doy, n_cells_lat, n_cells_lon), np.nan, dtype=np.float64)

# For each doy, compute for all cells at once using masked operations
for d in range(1, n_doy + 1):
    if d == 60:
        continue
    idx = doy_to_pool_idx_arr[d]
    if len(idx) == 0:
        continue
    pool_data = pool_sst[idx]  # (n_pool, 60, 60)
    
    # Mask: valid where finite and sea cell
    valid = np.isfinite(pool_data)  # (n_pool, 60, 60)
    # Also apply sea_cells mask
    valid &= sea_cells[None, :, :]
    
    # Compute mean ignoring NaN (climatology)
    counts = valid.sum(axis=0)
    sums = np.where(valid, pool_data, 0.0).sum(axis=0)
    climatology[d-1] = np.where(counts > 0, sums / np.maximum(counts, 1), np.nan)
    
    # Compute 90th percentile using hazen method
    # For each cell, get valid values and compute percentile
    for ci in range(n_cells_lat):
        for cj in range(n_cells_lon):
            if counts[ci, cj] > 0:
                vals = pool_data[:, ci, cj]
                vals_valid = vals[valid[:, ci, cj]]
                thresholds[d-1, ci, cj] = np.percentile(vals_valid, 90, method='hazen')

print("Done computing thresholds and climatology")

# Set day 60 = mean of 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2.0
climatology[59] = (climatology[58] + climatology[60]) / 2.0

# Verify
print("Day 59 threshold sample:", thresholds[58, 0, 0])
print("Day 60 threshold sample:", thresholds[59, 0, 0])
print("Day 61 threshold sample:", thresholds[60, 0, 0])
