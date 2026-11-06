
import numpy as np
import pandas as pd
from datetime import date, timedelta
from collections import defaultdict
import time

def day_of_year_custom(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Setup
start = date(1991, 12, 27)
end = date(2003, 1, 5)
all_dates = []
d = start
while d <= end:
    all_dates.append(d)
    d += timedelta(days=1)
all_dates = np.array(all_dates, dtype=object)
n_dates = len(all_dates)

base_start_d = date(1992, 1, 1)
base_end_d = date(2002, 12, 31)
base_mask = np.array([base_start_d <= x <= base_end_d for x in all_dates])

date_to_idx = {d: i for i, d in enumerate(all_dates)}

doy_to_base_dates = defaultdict(list)
for y in all_dates[base_mask]:
    d = day_of_year_custom(y)
    doy_to_base_dates[d].append(y)

doy_to_pool_mask = {}
for d in range(1, 367):
    if d == 60:
        continue
    pool_mask = np.zeros(n_dates, dtype=bool)
    for y in doy_to_base_dates[d]:
        y_idx = date_to_idx[y]
        lo = max(0, y_idx - 5)
        hi = min(n_dates, y_idx + 6)
        pool_mask[lo:hi] = True
    doy_to_pool_mask[d] = pool_mask

print("Setup complete.")

# Load data
import xarray as xr
path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

lat_idx = slice(217, 277)
lon_idx = slice(421, 481)
base_start_idx = 3647
base_end_idx = 7674
tgt_start_idx = 9282
tgt_end_idx = 9373

print("Loading baseline data...")
base_sub = ds.analysed_sst.isel(time=slice(base_start_idx, base_end_idx+1),
                                 latitude=lat_idx, longitude=lon_idx)
base_data = base_sub.values

print("Loading target data...")
tgt_sub = ds.analysed_sst.isel(time=slice(tgt_start_idx, tgt_end_idx+1),
                                latitude=lat_idx, longitude=lon_idx)
tgt_data = tgt_sub.values
ds.close()

print(f"Base shape: {base_data.shape}, tgt shape: {tgt_data.shape}")

# Sea cells
sea_cells = ~np.isnan(tgt_data).any(axis=0)
print(f"Sea cells: {sea_cells.sum()}")

# Compute thresholds and climatology
n_doy = 366
n_lat, n_lon = 60, 60
threshold = np.zeros((n_doy, n_lat, n_lon), dtype=np.float64)
climatology = np.zeros((n_doy, n_lat, n_lon), dtype=np.float64)

t0 = time.time()
for d in range(1, 367):
    if d == 60:
        continue
    pool_mask = doy_to_pool_mask[d]
    pool_indices = np.where(pool_mask)[0]
    pool_data = base_data[pool_indices]
    
    # Flatten spatial dims
    n_pool = len(pool_indices)
    pool_flat = pool_data.reshape(n_pool, -1)  # (n_pool, 3600)
    
    # Mean ignoring NaN
    means = np.nanmean(pool_flat, axis=0)
    
    # 90th percentile with hazen method
    p90 = np.nanpercentile(pool_flat, 90, axis=0, method='hazen')
    
    climatology[d-1] = means.reshape(n_lat, n_lon)
    threshold[d-1] = p90.reshape(n_lat, n_lon)

print(f"Computation done in {time.time()-t0:.2f}s")

# Set day 60
climatology[59] = (climatology[58] + climatology[60]) / 2.0
threshold[59] = (threshold[58] + threshold[60]) / 2.0

# Smooth with 31-day moving average wrapping around 366
# Day d averages days d-15 to d+15, counted modulo 366

def smooth_wrap(arr, window=31):
    """Smooth a 366-element array with centred 31-day moving mean wrapping around."""
    half = (window - 1) // 2  # 15
    result = np.zeros_like(arr)
    for i in range(366):
        idx = [(i + j) % 366 for j in range(-half, half + 1)]
        result[i] = np.mean(arr[idx])
    return result

t0 = time.time()
# Apply smoothing per cell
smoothed_threshold = np.zeros_like(threshold)
smoothed_climatology = np.zeros_like(climatology)

for lat in range(n_lat):
    for lon in range(n_lon):
        smoothed_threshold[:, lat, lon] = smooth_wrap(threshold[:, lat, lon])
        smoothed_climatology[:, lat, lon] = smooth_wrap(climatology[:, lat, lon])

print(f"Smoothing done in {time.time()-t0:.2f}s")

# Save intermediate results
np.save('/tmp/threshold_raw.npy', threshold)
np.save('/tmp/climatology_raw.npy', climatology)
np.save('/tmp/threshold_smoothed.npy', smoothed_threshold)
np.save('/tmp/climatology_smoothed.npy', smoothed_climatology)
np.save('/tmp/sea_cells.npy', sea_cells)

print("Saved intermediate results.")
print(f"Threshold shape: {smoothed_threshold.shape}")
print(f"Climatology shape: {smoothed_climatology.shape}")
