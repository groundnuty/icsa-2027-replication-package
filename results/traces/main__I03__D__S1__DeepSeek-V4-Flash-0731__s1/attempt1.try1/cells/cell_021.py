
import numpy as np
import datetime as dt
import xarray as xr
import json
import os
import gc

# ============================================================
# Load data
# ============================================================
print("Loading data...")
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat_min_idx, lat_max_idx = 34, 93
lon_min_idx, lon_max_idx = 213, 272

times = ds.time.values
lats = ds.latitude.values[lat_min_idx:lat_max_idx+1]
lons = ds.longitude.values[lon_min_idx:lon_max_idx+1]
n_lat, n_lon = len(lats), len(lons)

baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
target_start = np.datetime64('2014-06-01')
target_end = np.datetime64('2014-08-31')

baseline_mask = (times >= baseline_start) & (times <= baseline_end)
target_mask = (times >= target_start) & (times <= target_end)

baseline_idx = np.where(baseline_mask)[0]
target_idx = np.where(target_mask)[0]

baseline_sst = ds['analysed_sst'].isel(time=baseline_idx, latitude=slice(lat_min_idx, lat_max_idx+1), longitude=slice(lon_min_idx, lon_max_idx+1)).values.astype(np.float64)
target_sst = ds['analysed_sst'].isel(time=target_idx, latitude=slice(lat_min_idx, lat_max_idx+1), longitude=slice(lon_min_idx, lon_max_idx+1)).values.astype(np.float64)

baseline_dates = [dt.datetime.utcfromtimestamp(t.astype('datetime64[us]').astype(np.int64) / 1e6) for t in times[baseline_idx]]
target_dates = [dt.datetime.utcfromtimestamp(t.astype('datetime64[us]').astype(np.int64) / 1e6) for t in times[target_idx]]

del ds
gc.collect()

print(f"Baseline shape: {baseline_sst.shape}")
print(f"Target shape: {target_sst.shape}")

# ============================================================
# Step 1: Sea cells
# ============================================================
n_target_days = len(target_dates)
sea_cells = np.ones((n_lat, n_lon), dtype=bool)
for t in range(n_target_days):
    sea_cells &= np.isfinite(target_sst[t])
    
print(f"Sea cells: {np.sum(sea_cells)} out of {n_lat * n_lon}")

# ============================================================
# Step 2: Threshold and climatology
# ============================================================
# Define day-of-year mapping
def day_of_year(date):
    month = date.month
    day = date.day
    cum_days_before = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days_before[month - 1] + day

# Build baseline date mapping
baseline_dates_dt = [d.date() for d in baseline_dates]
core_start = dt.date(1992, 1, 1)
core_end = dt.date(2002, 12, 31)

date_to_idx = {}
for i, d in enumerate(baseline_dates_dt):
    date_to_idx[d] = i

# For each doy, find all core baseline dates
from collections import defaultdict
doy_to_core_dates = defaultdict(list)
for i, d in enumerate(baseline_dates_dt):
    if core_start <= d <= core_end:
        doy = day_of_year(d)
        doy_to_core_dates[doy].append(d)

# For each doy, find all indices in the pool
doy_to_indices = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    indices = set()
    for core_date in doy_to_core_dates[doy]:
        for delta in range(-5, 6):
            date = core_date + dt.timedelta(days=delta)
            if date in date_to_idx:
                indices.add(date_to_idx[date])
    doy_to_indices[doy] = sorted(indices)

# Print some stats
for doy in [1, 59, 61, 153, 244, 366]:
    n = len(doy_to_indices[doy])
    print(f"Day of year {doy}: {n} dates in pool")
    if n > 0:
        idxs = doy_to_indices[doy]
        print(f"  First: {baseline_dates_dt[idxs[0]]}, Last: {baseline_dates_dt[idxs[-1]]}")

# Save state for later cells
np.save('/work/sea_cells.npy', sea_cells)
np.save('/work/baseline_sst.npy', baseline_sst)
np.save('/work/target_sst.npy', target_sst)

import pickle
with open('/work/doy_to_indices.pkl', 'wb') as f:
    pickle.dump(doy_to_indices, f)
with open('/work/baseline_dates_dt.pkl', 'wb') as f:
    pickle.dump(baseline_dates_dt, f)
with open('/work/target_dates.pkl', 'wb') as f:
    pickle.dump(target_dates, f)
np.save('/work/lats.npy', lats)
np.save('/work/lons.npy', lons)
