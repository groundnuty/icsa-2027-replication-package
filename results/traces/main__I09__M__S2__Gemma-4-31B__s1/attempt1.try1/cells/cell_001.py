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
        smoothed[i] = np.mean(window)
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

# Subset region
ds_reg = ds.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

# Target SST
target_sst_ds = ds_reg.sel(time=slice(target_start, target_end))
target_sst = target_sst_ds.sst.values.astype(np.float64)
target_times = pd.to_datetime(target_sst_ds.time.values)

# Identify sea cells: finite SST on every day of target period
# target_sst shape: (time, lat, lon)
sea_cells_mask = np.all(np.isfinite(target_sst), axis=0)

# Baseline SST (include window margins)
# Baseline range 1992-01-01 to 2002-12-31, window +/- 5 days
# Overall range: 1991-12-27 to 2003-01-05
baseline_sst_ds = ds_reg.sel(time=slice('1991-12-27', '2003-01-05'))
baseline_sst = baseline_sst_ds.sst.values.astype(np.float64)
baseline_times = pd.to_datetime(baseline_sst_ds.time.values)

# Pre-calculate DOY for all baseline times
baseline_doys = np.array([get_doy(t) for t in baseline_times])

# Baseline indices for each DOY (excluding 60)
doy_to_baseline_indices = {d: [] for d in range(1, 367)}
for i, doy in enumerate(baseline_doys):
    # We only care about dates that fall within the core baseline period [1992-01-01, 2002-12-31]
    # to serve as the "center" of the +/- 5 day window.
    # Wait, the instructions say "baseline date (1992-01-01 to 2002-12-31) whose day of year is d".
    pass

# Let's re-evaluate baseline dates
core_baseline_start = pd.to_datetime(baseline_start)
core_baseline_end = pd.to_datetime(baseline_end)
core_baseline_times = baseline_times[(baseline_times >= core_baseline_start) & (baseline_times <= core_baseline_end)]

# For each DOY d from 1 to 366 (d != 60), find all core dates with that DOY.
# For each such date, the window is [date - 5, date + 5].
# These windows are then used to collect SST values.

# To optimize, let's map each date in the full baseline_sst range to its index
time_to_idx = {t: i for i, t in enumerate(baseline_times)}

# Pre-compute thresholds and climatology per cell
lat_size, lon_size = target_sst.shape[1:]
thresholds = np.zeros((lat_size, lon_size, 366), dtype=np.float64)
climatologies = np.zeros((lat_size, lon_size, 366), dtype=np.float64)

# We only need to compute for sea cells
sea_indices = np.argwhere(sea_cells_mask)

# To speed up, let's pre-calculate the pools of indices for each DOY
doy_pools = {}
for d in range(1, 367):
    if d == 60:
        continue
    
    pool_indices = []
    # Find core baseline dates with DOY d
    for b_date in core_baseline_times:
        if get_doy(b_date) == d:
            # Window [b_date - 5, b_date + 5]
            for offset in range(-5, 6):
                win_date = b_date + pd.Timedelta(days=offset)
                if win_date in time_to_idx:
                    pool_indices.append(time_to_idx[win_date])
    doy_pools[d] = np.unique(pool_indices)

# Compute threshold and climatology
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
        else:
            thresholds[r, c, d-1] = np.nan
            climatologies[r, c, d-1] = np.nan

# Handle Day 60
for r in range(lat_size):
    for c in range(lon_size):
        thresholds[r, c, 59] = (thresholds[r, c, 58] + thresholds[r, c, 60]) / 2
        climatologies[r, c, 59] = (climatologies[r, c, 58] + climatologies[r, c, 60]) / 2

# Smoothing
smoothed_thresholds = np.zeros_like(thresholds)
smoothed_climatologies = np.zeros_like(climatologies)
for r in range(lat_size):
    for c in range(lon_size):
        smoothed_thresholds[r, c, :] = smooth_366(thresholds[r, c, :])
        smoothed_climatologies[r, c, :] = smooth_366(climatologies[r, c, :])

# Per-cell MHWs
mhw_mask = np.zeros(target_sst.shape, dtype=np.uint8)
target_doys = np.array([get_doy(t) for t in target_times])

for r, c in sea_indices:
    cell_target_sst = target_sst[:, r, c]
    # hot days
    is_hot = np.zeros(len(target_times), dtype=bool)
    for i, doy in enumerate(target_doys):
        if cell_target_sst[i] >= smoothed_thresholds[r, c, doy-1]:
            is_hot[i] = True
            
    # Find MHW runs
    mhw_cell = np.zeros(len(target_times), dtype=bool)
    # 1. Find runs of >= 5 hot days
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
            
    # 2. Join gaps of 1 or 2 non-hot days
    # We need to repeat this until no more joins are possible, 
    # but based on the rules, a single pass of checking gaps between MHW segments is usually enough.
    # Let's do it carefully.
    changed = True
    while changed:
        changed = False
        # Current MHW segments
        # Find all segments of 1s
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
        
        # Join segments
        for j in range(len(segments)-1):
            end1 = segments[j][1]
            start2 = segments[j+1][0]
            gap = start2 - end1
            if 1 <= gap <= 2:
                # Join them
                mhw_cell[end1:start2] = True
                changed = True
                break # Restart to ensure all joins are handled
    
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

# mhw_mask.nc
# Need to use the original coordinate values from the dataset
mhw_xr = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw_mask)},
    coords={
        "time": target_sst_ds.time,
        "lat": ds_reg.lat,
        "lon": ds_reg.lon
    }
)
mhw_xr.to_netcdf('output/mhw_mask.nc')

# report.json
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
