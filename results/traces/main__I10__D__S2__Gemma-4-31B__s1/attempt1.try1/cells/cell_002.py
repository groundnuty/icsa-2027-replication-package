import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
import os
from datetime import datetime, timedelta

# 1. Configuration
lat_min, lat_max = 55.67, 56.87
lon_min, lon_max = 16.45, 17.65
baseline_start = '1992-01-01'
baseline_end = '2002-12-31'
target_start = '2005-06-01'
target_end = '2005-08-31'
baseline_buffer_start = '1991-12-27'
baseline_buffer_end = '2003-01-05'

# 2. Load and subset data
fs = fsspec.filesystem('onedata')
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
if not os.path.exists(local_path):
    fs.get(remote_path, local_path)

ds = xr.open_dataset(local_path, engine='h5netcdf')

# Region subset
ds_reg = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Time subsets
# Baseline buffer
ds_baseline = ds_reg.sel(time=slice(baseline_buffer_start, baseline_buffer_end))
# Target
ds_target = ds_reg.sel(time=slice(target_start, target_end))

# 3. Define Sea Cells
# Finite SST on every day of target period
sst_target = ds_target['analysed_sst'].values.astype(np.float64)
# sst_target shape: (time, lat, lon)
is_finite = np.all(np.isfinite(sst_target), axis=0)
sea_cells_mask = is_finite

# Keep only sea cells for calculations
# To keep indexing simple, we can just use the mask later, 
# but the prompt says "Sea cells are the region's grid cells whose SST is finite..."
# and "land cells are 0" in the mask.

# 4. Threshold and Climatology
sst_baseline = ds_baseline['analysed_sst'].values.astype(np.float64)
times_baseline = pd.to_datetime(ds_baseline.time.values)

def get_day_of_year(dt):
    # 1 Jan = 1, ..., 29 Feb = 60, ...
    return dt.timetuple().tm_yday

# We need a pool for each day of year d in [1, 366], d != 60.
# Pool consists of SST values from all dates T such that there exists B in [1992-01-01, 2002-12-31]
# where B has day of year d and |T - B| <= 5 days.

# Create a mapping of day of year to baseline dates
baseline_dates = pd.date_range(baseline_start, baseline_end)
doy_to_dates = {}
for bd in baseline_dates:
    d = bd.timetuple().tm_yday
    if d not in doy_to_dates:
        doy_to_dates[d] = []
    doy_to_dates[d].append(bd)

# Pre-calculate window for each d
# We need to find which indices in sst_baseline correspond to these windows
baseline_time_index = {t: i for i, t in enumerate(times_baseline)}

thresholds = np.full((366, sst_baseline.shape[1], sst_baseline.shape[2]), np.nan, dtype=np.float64)
climatology = np.full((366, sst_baseline.shape[1], sst_baseline.shape[2]), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    
    # Find all T such that |T-B| <= 5 for some B in [1992-01-01, 2002-12-31] with DOY d
    pool_indices = set()
    if d in doy_to_dates:
        for bd in doy_to_dates[d]:
            # Window [bd-5, bd+5]
            for offset in range(-5, 6):
                t_win = bd + timedelta(days=offset)
                if t_win in baseline_time_index:
                    pool_indices.add(baseline_time_index[t_win])
    
    if pool_indices:
        pool_data = sst_baseline[list(pool_indices), :, :]
        # Threshold: 90th percentile (method="hazen")
        # np.quantile(..., method="hazen") is what MATLAB's quantile does
        thresholds[d-1] = np.nanquantile(pool_data, 0.9, axis=0, method="hazen")
        climatology[d-1] = np.nanmean(pool_data, axis=0)

# Handle Day 60
thresholds[59] = (thresholds[58] + thresholds[60]) / 2.0
climatology[59] = (climatology[58] + climatology[60]) / 2.0

# 5. Smoothing
def smooth_31day(arr):
    # arr shape: (366, lat, lon)
    smoothed = np.zeros_like(arr)
    for d in range(366):
        # Window d-15 to d+15 modulo 366
        # d is 0-indexed, so day d+1 is index d.
        # Day 1 (index 0) window: indices -15...15 mod 366.
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window_data = arr[indices, :, :]
        smoothed[d] = np.nanmean(window_data, axis=0)
    return smoothed

thresholds_smooth = smooth_31day(thresholds)
climatology_smooth = smooth_31day(climatology)

# 6. Per-cell MHWs
# Target period: 2005-06-01 to 2005-08-31
target_times = pd.to_datetime(ds_target.time.values)
target_doys = [t.timetuple().tm_yday for t in target_times]

# Hot days: SST >= threshold
# sst_target shape (time, lat, lon)
# thresholds_smooth shape (366, lat, lon)
# Need to expand target_doys to index thresholds_smooth
# target_doys are 1-366, indices are 0-365
hot_days = np.zeros(sst_target.shape, dtype=bool)
for i, doy in enumerate(target_doys):
    hot_days[i] = sst_target[i] >= thresholds_smooth[doy-1]

# MHW logic: 
# - Run of >= 5 consecutive hot days
# - Gaps of 1-2 non-hot days joined
mhw_mask = np.zeros(sst_target.shape, dtype=bool)
lat_size, lon_size = sst_target.shape[1], sst_target.shape[2]

for lat in range(lat_size):
    for lon in range(lon_size):
        if not sea_cells_mask[lat, lon]:
            continue
        
        cell_hot = hot_days[:, lat, lon]
        # Find runs of hot days
        # A simple way to handle gaps:
        # First, find all runs of >= 5.
        # Then, expand them by filling gaps of 1-2.
        # Repeat until no more expansions.
        
        # Better approach: 
        # 1. Identify all hot runs.
        # 2. Any run < 5 is removed.
        # 3. Any gap <= 2 between remaining runs is filled.
        # 4. If filling a gap creates a run that was < 5 but now is >= 5... 
        # Actually, the rule is: "a per-cell MHW is a run of at least 5 consecutive hot days; 
        # per-cell MHWs separated by 1 or 2 non-hot days are joined".
        # This implies we first identify the "seeds" (runs of >= 5), then join them.
        
        # Finding runs of >= 5:
        runs = []
        start = None
        for i in range(len(cell_hot)):
            if cell_hot[i]:
                if start is None: start = i
            else:
                if start is not None:
                    if i - start >= 5:
                        runs.append([start, i - 1])
                    start = None
        if start is not None:
            if len(cell_hot) - start >= 5:
                runs.append([start, len(cell_hot) - 1])
        
        # Join runs separated by 1-2 days
        if not runs:
            continue
        
        merged = []
        if runs:
            curr_start, curr_end = runs[0]
            for next_start, next_end in runs[1:]:
                if next_start - curr_end - 1 <= 2:
                    curr_end = next_end
                else:
                    merged.append([curr_start, curr_end])
                    curr_start, curr_end = next_start, next_end
            merged.append([curr_start, curr_end])
        
        for s, e in merged:
            mhw_mask[s:e+1, lat, lon] = True

# 7. Regional Events
# active_day: at least one sea cell is in MHW
active_days = np.any(mhw_mask, axis=(1, 2))
regional_events = []
start = None
for i in range(len(active_days)):
    if active_days[i]:
        if start is None: start = i
    else:
        if start is not None:
            regional_events.append([target_times[start], target_times[i-1]])
            start = None
if start is not None:
    regional_events.append([target_times[start], target_times[-1]])

# 8. Output files
# NetCDF mask
mask_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask.astype(np.uint8))},
    coords={
        "time": ds_target.time,
        "latitude": ds_reg.latitude,
        "longitude": ds_reg.longitude,
    }
)
os.makedirs('output', exist_ok=True)
mask_ds.to_netcdf('output/mhw_mask.nc')

# JSON report
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": baseline_buffer_start, "end": baseline_buffer_end},
    "target_analysed": {"start": target_start, "end": target_end},
    "events": [{"onset": e[0].strftime('%Y-%m-%d'), "end": e[1].strftime('%Y-%m-%d')} for e in regional_events],
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Processing complete.")
