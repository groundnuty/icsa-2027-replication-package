import xarray as xr
import numpy as np
import pandas as pd
import json
import fsspec
from datetime import datetime, date, timedelta
import os

def get_custom_doy(dt):
    # Map date to 1-366 based on a leap year (2000)
    # 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366
    return date(2000, dt.month, dt.day).timetuple().tm_yday

# Setup filesystem
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

# Region and time bounds
lat_min, lat_max = 57.85, 59.05
lon_min, lon_max = 21.01, 22.21
target_start_str = "2013-06-01"
target_end_str = "2013-08-31"
baseline_start_str = "1992-01-01"
baseline_end_str = "2002-12-31"

# Open dataset and load the subset into memory
with fs.open(path, "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")
    # Subset region and load
    ds_reg = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max)).load()

# Target period subset for sea cell identification
target_start = pd.Timestamp(target_start_str)
target_end = pd.Timestamp(target_end_str)
ds_target = ds_reg.sel(time=slice(target_start, target_end))

# 1. Sea cells: SST is finite on every day of the target period
sst_target = ds_target['analysed_sst']
sea_cells_mask = np.isfinite(sst_target).all(dim='time')

# 2. Threshold and climatology
baseline_start = pd.Timestamp(baseline_start_str)
baseline_end = pd.Timestamp(baseline_end_str)

# Range for pool data: baseline +/- 5 days
pool_range_start = baseline_start - pd.Timedelta(days=5)
pool_range_end = baseline_end + pd.Timedelta(days=5)
ds_pool_data = ds_reg.sel(time=slice(pool_range_start, pool_range_end))

times = pd.to_datetime(ds_pool_data.time.values)
sst_values = ds_pool_data['analysed_sst'].values.astype(np.float64)

nlat = len(ds_reg.latitude)
nlon = len(ds_reg.longitude)
thresholds_all = np.full((366, nlat, nlon), np.nan, dtype=np.float64)
climatology_all = np.full((366, nlat, nlon), np.nan, dtype=np.float64)

# Baseline mask and days
baseline_mask = (times >= baseline_start) & (times <= baseline_end)
baseline_times = times[baseline_mask]
baseline_doys = np.array([get_custom_doy(t) for t in baseline_times])

# Pools for d in 1..366, d != 60
doy_pools = {}
for d in range(1, 367):
    if d == 60:
        continue
    # Baseline dates with doy d
    b_dates_with_d = baseline_times[baseline_doys == d]
    pool_indices = set()
    for b_date in b_dates_with_d:
        # Window [b_date - 5, b_date + 5]
        start_idx = np.searchsorted(times, b_date - pd.Timedelta(days=5))
        end_idx = np.searchsorted(times, b_date + pd.Timedelta(days=5), side='right')
        pool_indices.update(range(start_idx, end_idx))
    doy_pools[d] = list(pool_indices)

# Compute for sea cells
sea_indices = np.argwhere(sea_cells_mask.values)
for i, j in sea_indices:
    cell_sst = sst_values[:, i, j]
    for d, indices in doy_pools.items():
        pool = cell_sst[indices]
        pool = pool[~np.isnan(pool)]
        if len(pool) > 0:
            thresholds_all[d-1, i, j] = np.quantile(pool, 0.9, method='hazen')
            climatology_all[d-1, i, j] = np.nanmean(pool)

# Set day 60 to mean of 59 and 61
thresholds_all[59] = (thresholds_all[58] + thresholds_all[60]) / 2
climatology_all[59] = (climatology_all[58] + climatology_all[60]) / 2

# Smoothing: 31-day centred moving mean (wrap around)
def smooth_31(arr):
    smoothed = np.full_like(arr, np.nan)
    for d in range(366):
        indices = [(d + k) % 366 for k in range(-15, 16)]
        smoothed[d] = np.nanmean(arr[indices], axis=0)
    return smoothed

thresholds_smoothed = smooth_31(thresholds_all)
climatology_smoothed = smooth_31(climatology_all)

# 3. Per-cell MHWs
target_times = pd.to_datetime(ds_target.time.values)
target_doy_custom = np.array([get_custom_doy(t) for t in target_times])
target_sst_vals = sst_target.values.astype(np.float64)

hot_days = np.zeros(target_sst_vals.shape, dtype=bool)
for t in range(len(target_times)):
    d = target_doy_custom[t]
    hot_days[t] = target_sst_vals[t] >= thresholds_smoothed[d-1]

mhw_mask = np.zeros(target_sst_vals.shape, dtype=np.uint8)
for i, j in sea_indices:
    cell_hot = hot_days[:, i, j]
    n_days = len(cell_hot)
    is_mhw = np.zeros(n_days, dtype=bool)
    
    # Find initial runs of >= 5 hot days
    run_start = None
    for t in range(n_days):
        if cell_hot[t]:
            if run_start is None:
                run_start = t
        else:
            if run_start is not None:
                if t - run_start >= 5:
                    is_mhw[run_start:t] = True
                run_start = None
    if run_start is not None and n_days - run_start >= 5:
        is_mhw[run_start:n_days] = True
    
    # Join gaps of 1 or 2 non-hot days
    while True:
        changed = False
        temp_mhw = is_mhw.copy()
        # Gap of 1
        for t in range(1, n_days - 1):
            if not is_mhw[t] and is_mhw[t-1] and is_mhw[t+1]:
                temp_mhw[t] = True
                changed = True
        # Gap of 2
        for t in range(1, n_days - 2):
            if not is_mhw[t] and not is_mhw[t+1] and is_mhw[t-1] and is_mhw[t+2]:
                temp_mhw[t] = True
                temp_mhw[t+1] = True
                changed = True
        is_mhw = temp_mhw
        if not changed:
            break
    mhw_mask[:, i, j] = is_mhw.astype(np.uint8)

# 4. Regional events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
run_start = None
for t in range(len(active_days)):
    if active_days[t]:
        if run_start is None:
            run_start = t
    else:
        if run_start is not None:
            regional_events.append({
                "onset": target_times[run_start].strftime('%Y-%m-%d'),
                "end": target_times[t-1].strftime('%Y-%m-%d')
            })
            run_start = None
if run_start is not None:
    regional_events.append({
        "onset": target_times[run_start].strftime('%Y-%m-%d'),
        "end": target_times[-1].strftime('%Y-%m-%d')
    })

# Save output
os.makedirs('output', exist_ok=True)

ds_out = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": ds_target.time,
        "latitude": ds_reg.latitude,
        "longitude": ds_reg.longitude
    }
)
ds_out.to_netcdf('output/mhw_mask.nc')

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": baseline_start_str, "end": baseline_end_str},
    "target_analysed": {"start": target_start_str, "end": target_end_str},
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Analysis complete.")
