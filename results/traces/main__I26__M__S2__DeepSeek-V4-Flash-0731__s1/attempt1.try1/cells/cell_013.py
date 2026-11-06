
import numpy as np
import pandas as pd
from datetime import date, timedelta
from collections import defaultdict
import time

# Recompute all the setup
def day_of_year_custom(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

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

# Store this for later use
import pickle
with open('/tmp/setup.pkl', 'wb') as f:
    pickle.dump({
        'doy_to_pool_mask': doy_to_pool_mask,
    }, f)

print("Setup saved.")

# Compute thresholds and climatology
# For each sea cell and doy, compute 90th percentile and mean from pool
# base_data shape: (4028, 60, 60)
# sea_cells shape: (60, 60)

# Load base data
import xarray as xr
path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

lat_idx = slice(217, 277)
lon_idx = slice(421, 481)
base_start_idx = 3647
base_end_idx = 7674

base_sub = ds.analysed_sst.isel(time=slice(base_start_idx, base_end_idx+1),
                                 latitude=lat_idx, longitude=lon_idx)
base_data = base_sub.values  # (4028, 60, 60)
ds.close()

tgt_start_idx = 9282
tgt_end_idx = 9373
# We'll load target data later

# Sea cells from earlier computation
tgt_sub = xr.open_dataset(path, engine='h5netcdf').analysed_sst.isel(
    time=slice(tgt_start_idx, tgt_end_idx+1), latitude=lat_idx, longitude=lon_idx)
tgt_data = tgt_sub.values
sea_cells = ~np.isnan(tgt_data).any(axis=0)

print(f"Sea cells: {sea_cells.sum()}, base data shape: {base_data.shape}")

# Compute thresholds and climatology
# Initialize arrays
n_doy = 366
n_lat, n_lon = 60, 60
threshold = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)

# For each doy, compute threshold and climatology for sea cells
for d in range(1, 367):
    if d == 60:
        continue
    pool_mask = doy_to_pool_mask[d]
    pool_indices = np.where(pool_mask)[0]
    
    # Extract data for pool dates: (n_pool, 60, 60)
    pool_data = base_data[pool_indices]  # This might be big if many pool dates
    
    # For each cell, compute stats
    # pool_data shape: (n_pool, n_lat, n_lon)
    # Reshape to (n_pool, n_lat*n_lon)
    n_pool = len(pool_indices)
    pool_flat = pool_data.reshape(n_pool, -1)  # (n_pool, 3600)
    
    # Compute mean ignoring NaN
    with np.errstate(invalid='ignore'):
        means = np.nanmean(pool_flat, axis=0)  # (3600,)
    
    # Compute 90th percentile using hazen method
    # numpy.quantile with method='hazen'
    p90 = np.nanpercentile(pool_flat, 90, axis=0, method='hazen')  # (3600,)
    
    # Reshape back
    climatology[d-1] = means.reshape(n_lat, n_lon)
    threshold[d-1] = p90.reshape(n_lat, n_lon)
    
    if d % 50 == 0:
        print(f"doy={d}: done, pool size={n_pool}")

print("\nComputation complete for all doys except 60.")

# Set day 60 to mean of days 59 and 61
climatology[59] = (climatology[58] + climatology[60]) / 2.0
threshold[59] = (threshold[58] + threshold[60]) / 2.0
print("Day 60 set to mean of days 59 and 61.")
