
import numpy as np
from datetime import date, timedelta
from collections import defaultdict

# ===== Step 0: Load data =====
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
print("Loaded sst:", sst.shape, sst.dtype)

pool_local = np.where(pool_mask[time_idx])[0]
target_local = np.where(target_mask[time_idx])[0]

# ===== Step 1: Sea cells =====
# Sea cells = cells with finite SST on every day of target period
target_sst = sst[target_local]  # (92, 60, 60)
sea_cells = np.all(np.isfinite(target_sst), axis=0)  # (60, 60)
print("Sea cells:", sea_cells.sum(), "of", sea_cells.size)

# ===== Step 2: Compute pools, thresholds, climatology =====
def doy_map(d):
    months = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(months[:d.month-1]) + d.day

# Build baseline dates set
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

# ===== Step 3: Compute threshold and climatology for each sea cell =====
n_cells_lat, n_cells_lon = 60, 60
n_doy = 366

# Pool SST for each sea cell and doy
# sst[pool_local] has shape (4028, 60, 60)
pool_sst = sst[pool_local]  # (4028, 60, 60), float64

# For each doy d, compute threshold and climatology for each sea cell
# This is the expensive part
thresholds = np.full((n_doy, n_cells_lat, n_cells_lon), np.nan, dtype=np.float64)
climatology = np.full((n_doy, n_cells_lat, n_cells_lon), np.nan, dtype=np.float64)

for d in range(1, n_doy + 1):
    if d == 60:
        continue
    idx = doy_to_pool_idx_arr[d]
    if len(idx) == 0:
        continue
    pool_data = pool_sst[idx]  # (n_pool, 60, 60)
    
    # For each cell, compute 90th percentile (method='hazen') and mean, ignoring NaN
    # Use nanpercentile with method='hazen'
    for ci in range(n_cells_lat):
        for cj in range(n_cells_lon):
            if not sea_cells[ci, cj]:
                continue
            vals = pool_data[:, ci, cj]
            # Remove NaN
            vals_valid = vals[np.isfinite(vals)]
            if len(vals_valid) == 0:
                continue
            thresholds[d-1, ci, cj] = np.percentile(vals_valid, 90, method='hazen')
            climatology[d-1, ci, cj] = np.mean(vals_valid)

print("Computed thresholds and climatology")
print("Non-NaN thresholds:", np.isfinite(thresholds).sum())
print("Non-NaN climatology:", np.isfinite(climatology).sum())
