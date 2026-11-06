import xarray as xr
import fsspec
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta

# Create output directory
os.makedirs('output', exist_ok=True)

def get_doy_custom(dt):
    month = dt.month
    day = dt.day
    month_starts = {
        1: 0, 2: 31, 3: 59, 4: 90, 5: 120, 6: 151, 
        7: 181, 8: 212, 9: 243, 10: 273, 11: 304, 12: 334
    }
    if month == 2 and day == 29:
        return 60
    if month <= 2:
        return month_starts[month] + day
    else:
        return month_starts[month] + day + 1

# Parameters
lat_min, lat_max = 57.13, 58.33
lon_min, lon_max = 22.79, 23.99
target_start = "2014-06-01"
target_end = "2014-08-31"
baseline_start = "1992-01-01"
baseline_end = "2002-12-31"
baseline_ext_start = "1991-12-27"
baseline_ext_end = "2003-01-05"

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    
    # Load data into memory to avoid "closed file" errors
    baseline_ds = region_ds.sel(time=slice(baseline_ext_start, baseline_ext_end)).load()
    target_ds = region_ds.sel(time=slice(target_start, target_end)).load()

# Data arrays (double precision)
sst_baseline = baseline_ds['analysed_sst'].astype(np.float64).values
sst_target = target_ds['analysed_sst'].astype(np.float64).values
baseline_times = pd.to_datetime(baseline_ds.time.values)
target_times = pd.to_datetime(target_ds.time.values)

# Region dimensions
n_lat = sst_baseline.shape[1]
n_lon = sst_baseline.shape[2]
n_time_t = sst_target.shape[0]

# Doy mappings
baseline_doys = np.array([get_doy_custom(t) for t in baseline_times])
target_doys = np.array([get_doy_custom(t) for t in target_times])

# Thresholds and climatologies (double precision)
thresholds = np.full((n_lat, n_lon, 367), np.nan, dtype=np.float64)
climatologies = np.full((n_lat, n_lon, 367), np.nan, dtype=np.float64)

# Baseline filter (1992-01-01 to 2002-12-31)
baseline_mask_range = (baseline_times >= pd.Timestamp(baseline_start)) & \
                      (baseline_times <= pd.Timestamp(baseline_end))

for d in range(1, 367):
    if d == 60:
        continue
    
    # Baseline dates with doy == d
    target_baseline_dates = baseline_times[baseline_mask_range & (baseline_doys == d)]
    
    pool_indices = []
    for date in target_baseline_dates:
        start_win = date - timedelta(days=5)
        end_win = date + timedelta(days=5)
        idx_start = np.searchsorted(baseline_times, start_win)
        idx_end = np.searchsorted(baseline_times, end_win, side='right')
        pool_indices.extend(range(idx_start, idx_end))
    
    pool_indices = sorted(list(set(pool_indices)))
    
    if pool_indices:
        pool_data = sst_baseline[pool_indices, :, :]
        # 90th percentile (hazen) and mean
        thresholds[:, :, d] = np.nanquantile(pool_data, 0.9, axis=0, method='hazen')
        climatologies[:, :, d] = np.nanmean(pool_data, axis=0)

# Day 60 handled by average of 59 and 61
thresholds[:, :, 60] = (thresholds[:, :, 59] + thresholds[:, :, 61]) / 2
climatologies[:, :, 60] = (climatologies[:, :, 59] + climatologies[:, :, 61]) / 2

# Smoothing: 31-day centered moving mean, wrap around
def smooth_array(arr):
    # arr is (lat, lon, 367), we only use indices 1..366
    data = arr[:, :, 1:] # (lat, lon, 366)
    res = np.full_like(data, np.nan)
    for d in range(366):
        window = [(d + i) % 366 for i in range(-15, 16)]
        res[:, :, d] = np.nanmean(data[:, :, window], axis=2)
    
    smoothed = np.full((n_lat, n_lon, 367), np.nan, dtype=np.float64)
    smoothed[:, :, 1:] = res
    return smoothed

thresholds_smoothed = smooth_array(thresholds)

# Sea cells: SST is finite on every day of the target period
is_sea = np.all(np.isfinite(sst_target), axis=0)

# Target period detection
target_thresholds = thresholds_smoothed[:, :, target_doys] # (lat, lon, time)
target_thresholds = np.transpose(target_thresholds, (2, 0, 1)) # (time, lat, lon)

hot = sst_target >= target_thresholds
mhw_mask = np.zeros_like(hot, dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not is_sea[i, j]:
            continue
        
        cell_hot = hot[:, i, j]
        hot_int = cell_hot.astype(int)
        diff = np.diff(np.concatenate(([0], hot_int, [0])))
        starts = np.where(diff == 1)[0]
        ends = np.where(diff == -1)[0]
        
        mhw_runs = []
        for s, e in zip(starts, ends):
            if e - s >= 5:
                mhw_runs.append([s, e])
        
        if not mhw_runs:
            continue
            
        merged = []
        curr_s, curr_e = mhw_runs[0]
        for next_s, next_e in mhw_runs[1:]:
            gap = next_s - curr_e
            if gap <= 2:
                curr_e = next_e
            else:
                merged.append((curr_s, curr_e))
                curr_s, curr_e = next_s, next_e
        merged.append((curr_s, curr_e))
        
        for s, e in merged:
            mhw_mask[s:e, i, j] = 1

# Regional events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
diff_active = np.diff(np.concatenate(([0], active_days, [0])))
starts_reg = np.where(diff_active == 1)[0]
ends_reg = np.where(diff_active == -1)[0]

events = []
for s, e in zip(starts_reg, ends_reg):
    events.append({
        "onset": target_times[s].strftime('%Y-%m-%d'),
        "end": target_times[e-1].strftime('%Y-%m-%d')
    })

# Output files
mask_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": target_ds.time,
        "latitude": target_ds.latitude,
        "longitude": target_ds.longitude,
    }
)
mask_ds.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": baseline_start, "end": baseline_end},
    "target_analysed": {"start": target_start, "end": target_end},
    "events": events,
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Done")
