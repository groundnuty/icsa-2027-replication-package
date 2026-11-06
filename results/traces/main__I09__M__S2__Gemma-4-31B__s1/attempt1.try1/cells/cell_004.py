import xarray as xr
import numpy as np
import pandas as pd
import json
import os
from datetime import datetime, timedelta

def get_doy(date):
    """Map date to day of year 1-366 as per instructions."""
    y = date.year
    is_leap = (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0))
    doy = date.timetuple().tm_yday
    if not is_leap and doy >= 60:
        doy += 1
    return doy

def smooth_366(arr):
    """31-day centered moving mean with wrap-around for a 366-element array."""
    smoothed = np.zeros(366, dtype=np.float64)
    for i in range(366):
        window = []
        for k in range(-15, 16):
            idx = (i + k) % 366
            window.append(arr[idx])
        smoothed[i] = np.nanmean(window)
    return smoothed

# Parameters
file_path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
lat_min, lat_max = 54.81, 56.01
lon_min, lon_max = 19.61, 20.81
target_start = '2022-06-01'
target_end = '2022-08-31'
baseline_start = '1992-01-01'
baseline_end = '2002-12-31'

# Open dataset
ds = xr.open_dataset(file_path, engine="h5netcdf")

# Subset region (bounds inclusive)
# Using slice(lat_min, lat_max) might not be inclusive or might depend on order
# Since we want inclusive, we use .sel with method='nearest' or slice. 
# But the coords are usually sorted. Let's check.
lat_coords = ds.latitude.values
lon_coords = ds.longitude.values
lat_mask = (lat_coords >= lat_min) & (lat_coords <= lat_max)
lon_mask = (lon_coords >= lon_min) & (lon_coords <= lon_max)

ds_reg = ds.isel(latitude=lat_mask, longitude=lon_mask)

# Target SST
target_sst_ds = ds_reg.sel(time=slice(target_start, target_end))
target_sst = target_sst_ds.analysed_sst.values.astype(np.float64)
target_times = pd.to_datetime(target_sst_ds.time.values)

# Identify sea cells: finite SST on every day of target period
sea_cells_mask = np.all(np.isfinite(target_sst), axis=0)

# Baseline SST (include window margins)
# Overall range: 1991-12-27 to 2003-01-05
baseline_sst_ds = ds_reg.sel(time=slice('1991-12-27', '2003-01-05'))
baseline_sst = baseline_sst_ds.analysed_sst.values.astype(np.float64)
baseline_times = pd.to_datetime(baseline_sst_ds.time.values)

# Core baseline period
core_baseline_start = pd.to_datetime(baseline_start)
core_baseline_end = pd.to_datetime(baseline_end)
core_baseline_times = baseline_times[(baseline_times >= core_baseline_start) & (baseline_times <= core_baseline_end)]

# Map each date in the full baseline_sst range to its index
time_to_idx = {t: i for i, t in enumerate(baseline_times)}

# Pre-compute pools of indices for each DOY
doy_pools = {}
for d in range(1, 367):
    if d == 60:
        continue
    
    pool_dates = set()
    for b_date in core_baseline_times:
        if get_doy(b_date) == d:
            for offset in range(-5, 6):
                win_date = b_date + pd.Timedelta(days=offset)
                if win_date in time_to_idx:
                    pool_dates.add(win_date)
    
    doy_pools[d] = np.array([time_to_idx[dt] for dt in pool_dates])

# Compute thresholds and climatology per cell
lat_size, lon_size = target_sst.shape[1:]
thresholds = np.full((lat_size, lon_size, 366), np.nan, dtype=np.float64)
climatologies = np.full((lat_size, lon_size, 366), np.nan, dtype=np.float64)

sea_indices = np.argwhere(sea_cells_mask)

for r, c in sea_indices:
    cell_sst = baseline_sst[:, r, c]
    for d in range(1, 367):
        if d == 60:
            continue
        pool = cell_sst[doy_pools[d]]
        pool = pool[np.isfinite(pool)]
        if pool.size > 0:
            thresholds[r, c, d-1] = np.quantile(pool, 0.9, method="hazen")
            climatologies[r, c, d-1] = np.mean(pool)

# Handle Day 60: mean of days 59 and 61
for r in range(lat_size):
    for c in range(lon_size):
        thresholds[r, c, 59] = np.nanmean([thresholds[r, c, 58], thresholds[r, c, 60]])
        climatologies[r, c, 59] = np.nanmean([climatologies[r, c, 58], climatologies[r, c, 60]])

# Smoothing
smoothed_thresholds = np.full((lat_size, lon_size, 366), np.nan, dtype=np.float64)
smoothed_climatologies = np.full((lat_size, lon_size, 366), np.nan, dtype=np.float64)
for r in range(lat_size):
    for c in range(lon_size):
        smoothed_thresholds[r, c, :] = smooth_366(thresholds[r, c, :])
        smoothed_climatologies[r, c, :] = smooth_366(climatologies[r, c, :])

# Per-cell MHWs
mhw_mask = np.zeros(target_sst.shape, dtype=np.uint8)
target_doys = np.array([get_doy(t) for t in target_times])

for r, c in sea_indices:
    cell_target_sst = target_sst[:, r, c]
    is_hot = np.zeros(len(target_times), dtype=bool)
    for i, doy in enumerate(target_doys):
        thresh = smoothed_thresholds[r, c, doy-1]
        if not np.isnan(thresh) and cell_target_sst[i] >= thresh:
            is_hot[i] = True
            
    mhw_cell = np.zeros(len(target_times), dtype=bool)
    i = 0
    while i < len(is_hot):
        if is_hot[i]:
            start = i
            while i < len(is_hot) and is_hot[i]:
                i += 1
            if i - start >= 5:
                mhw_cell[start:i] = True
        else:
            i += 1
            
    changed = True
    while changed:
        changed = False
        segments = []
        i = 0
        while i < len(mhw_cell):
            if mhw_cell[i]:
                start = i
                while i < len(mhw_cell) and mhw_cell[i]:
                    i += 1
                segments.append((start, i))
            else:
                i += 1
        
        for j in range(len(segments)-1):
            end1 = segments[j][1]
            start2 = segments[j+1][0]
            gap = start2 - end1
            if 1 <= gap <= 2:
                mhw_cell[end1:start2] = True
                changed = True
                break
    
    mhw_mask[:, r, c] = mhw_cell.astype(np.uint8)

# Regional Events
regional_active = np.any(mhw_mask == 1, axis=(1, 2))
events = []
i = 0
while i < len(regional_active):
    if regional_active[i]:
        start = i
        while i < len(regional_active) and regional_active[i]:
            i += 1
        events.append({
            "onset": target_times[start].strftime('%Y-%m-%d'),
            "end": target_times[i-1].strftime('%Y-%m-%d')
        })
    else:
        i += 1

# Create output files
os.makedirs('output', exist_ok=True)

mhw_xr = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": target_sst_ds.time,
        "latitude": ds_reg.latitude,
        "longitude": ds_reg.longitude
    }
)
mhw_xr.to_netcdf('output/mhw_mask.nc')

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {
        "start": core_baseline_times[0].strftime('%Y-%m-%d'),
        "end": core_baseline_times[-1].strftime('%Y-%m-%d')
    },
    "target_analysed": {
        "start": target_times[0].strftime('%Y-%m-%d'),
        "end": target_times[-1].strftime('%Y-%m-%d')
    },
    "events": events,
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Processing complete.")
