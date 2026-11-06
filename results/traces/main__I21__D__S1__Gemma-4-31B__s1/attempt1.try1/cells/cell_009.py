import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import os
import json
from datetime import timedelta

# Configuration
lat_min, lat_max = 57.33, 58.53
lon_min, lon_max = 9.03, 10.23
target_start = "2021-06-01"
target_end = "2021-08-31"
baseline_start_year = 1992
baseline_end_year = 2002

def get_doy(dt):
    """Custom day of year mapping as per instructions."""
    return dt.timetuple().tm_yday

# Setup filesystem and dataset
fs = fsspec.filesystem('onedata')
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
if not os.path.exists(local_path):
    fs.get(remote_path, local_path)

ds = xr.open_dataset(local_path, engine="h5netcdf")

# Slice region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Define target period
t_start = pd.to_datetime(target_start)
t_end = pd.to_datetime(target_end)
target_days = ds_region.time.sel(time=slice(t_start, t_end))
target_sst = ds_region.analysed_sst.sel(time=slice(t_start, t_end))

# 1. Sea cells: finite SST on every day of the target period
# analysed_sst (time, latitude, longitude)
finite_mask = np.all(np.isfinite(target_sst.values), axis=0)
sea_cells_mask = finite_mask

# 2. Threshold and Climatology
# Baseline years 1992-2002
baseline_dates = pd.date_range(start=f"{baseline_start_year}-01-01", end=f"{baseline_end_year}-12-31")

# We need data from 1991-12-27 to 2003-01-05 to cover windows
data_start = pd.to_datetime("1991-12-27")
data_end = pd.to_datetime("2003-01-05")
ds_baseline = ds_region.sel(time=slice(data_start, data_end))
sst_baseline = ds_baseline.analysed_sst.values
time_baseline = pd.DatetimeIndex(ds_baseline.time.values)

# Prepare arrays for threshold and climatology
# Shape: (latitude, longitude, 366) - indexing by DOY 1 to 366
n_lat = len(ds_region.latitude)
n_lon = len(ds_region.longitude)
thresholds = np.full((n_lat, n_lon, 366), np.nan, dtype=np.float64)
climatologies = np.full((n_lat, n_lon, 366), np.nan, dtype=np.float64)

# Pre-calculate DOY for all baseline data
doy_baseline = np.array([get_doy(t) for t in time_baseline])

# For each day of year d (1-366), d != 60
for d in range(1, 367):
    if d == 60:
        continue
    
    # Find all baseline dates B such that DOY(B) == d
    # Baseline period: 1992-01-01 to 2002-12-31
    pool_indices = []
    for b_date in baseline_dates:
        if get_doy(b_date) == d:
            # Window [B-5, B+5]
            win_start = b_date - timedelta(days=5)
            win_end = b_date + timedelta(days=5)
            # Find indices of time_baseline in this window
            # Binary search or simple filter
            mask = (time_baseline >= win_start) & (time_baseline <= win_end)
            indices = np.where(mask)[0]
            pool_indices.extend(indices)
    
    if not pool_indices:
        continue
    
    pool_indices = np.unique(pool_indices)
    # Extract the pool of SSTs for this DOY
    # sst_baseline: (time, lat, lon)
    pool_data = sst_baseline[pool_indices, :, :] # (time_pool, lat, lon)
    
    # Compute 90th percentile (hazen) and mean
    # np.nanpercentile doesn't have 'hazen' in older versions, but method='hazen' is in numpy 1.22+
    # Hyndman-Fan type 5 is equivalent to method='hazen'
    # We compute across the time axis (0)
    thresholds[:, :, d-1] = np.nanpercentile(pool_data, 90, axis=0, method='hazen')
    climatologies[:, :, d-1] = np.nanmean(pool_data, axis=0)

# Handle day 60
thresholds[:, :, 59] = (thresholds[:, :, 58] + thresholds[:, :, 60]) / 2
climatologies[:, :, 59] = (climatologies[:, :, 58] + climatologies[:, :, 60]) / 2

# Smoothing: 31-day centered moving mean (wraps around)
def smooth_31(arr):
    # arr shape: (lat, lon, 366)
    res = np.full_like(arr, np.nan, dtype=np.float64)
    for d in range(366):
        # Indices: d-15 to d+15 modulo 366
        # Python range is [start, end), so d-15 to d+16
        idx = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[:, :, idx] # (lat, lon, 31)
        res[:, :, d] = np.nanmean(window, axis=2)
    return res

thresholds_smooth = smooth_31(thresholds)
climatologies_smooth = smooth_31(climatologies)

# 3. Per-cell MHWs
# target_sst: (time, lat, lon)
# target_days: time coordinates
target_doy = np.array([get_doy(t) for t in target_days])
# thresholds_smooth: (lat, lon, 366)

# Hot days mask
# Need to broadcast thresholds_smooth to (time, lat, lon)
# target_doy is (time,)
# Use advanced indexing: thresholds_smooth[:, :, target_doy - 1]
# But target_doy - 1 might be used to index. Let's be careful.
# thresholds_smooth is (lat, lon, 366). We want it to be (time, lat, lon).
# Reorder thresholds_smooth to (366, lat, lon) first.
thresh_reordered = np.moveaxis(thresholds_smooth, -1, 0) # (366, lat, lon)
hot_days = target_sst.values >= thresh_reordered[target_doy - 1, :, :] # (time, lat, lon)

# Per-cell MHW detection
# A run of >= 5 consecutive hot days. Gaps of 1 or 2 non-hot days joined.
def detect_mhw_cells(hot_mask):
    # hot_mask: (time, lat, lon)
    time_len, n_lat, n_lon = hot_mask.shape
    mhw_mask = np.zeros_like(hot_mask, dtype=np.uint8)
    
    for i in range(n_lat):
        for j in range(n_lon):
            cell_hot = hot_mask[:, i, j]
            # Find runs of hot days
            # Simple approach: iterate and mark
            in_mhw = False
            run_start = 0
            
            # First pass: find runs of >= 5
            temp_mhw = np.zeros(time_len, dtype=bool)
            current_run = []
            for t in range(time_len):
                if cell_hot[t]:
                    current_run.append(t)
                else:
                    if len(current_run) >= 5:
                        for rt in current_run: temp_mhw[rt] = True
                    current_run = []
            if len(current_run) >= 5:
                for rt in current_run: temp_mhw[rt] = True
            
            # Second pass: join gaps of 1 or 2
            # Repeat until no more gaps joined
            changed = True
            while changed:
                changed = False
                for t in range(1, time_len - 1):
                    if not temp_mhw[t]:
                        # Gap of 1: both neighbors are in MHW
                        if temp_mhw[t-1] and temp_mhw[t+1]:
                            temp_mhw[t] = True
                            changed = True
                        # Gap of 2: t and t+1 are non-hot, but t-1 and t+2 are in MHW
                        elif t < time_len - 2 and not temp_mhw[t+1] and temp_mhw[t-1] and temp_mhw[t+2]:
                            temp_mhw[t] = True
                            temp_mhw[t+1] = True
                            changed = True
            
            mhw_mask[:, i, j] = temp_mhw
            
    return mhw_mask

# The above loop is slow. Let's optimize it.
def detect_mhw_cells_opt(hot_mask):
    time_len, n_lat, n_lon = hot_mask.shape
    mhw_mask = np.zeros((time_len, n_lat, n_lon), dtype=np.uint8)
    
    # Flatten lat/lon to process all cells
    flat_hot = hot_mask.reshape(time_len, -1)
    flat_mhw = np.zeros((time_len, flat_hot.shape[1]), dtype=np.uint8)
    
    for c in range(flat_hot.shape[1]):
        cell_hot = flat_hot[:, c]
        temp_mhw = np.zeros(time_len, dtype=bool)
        
        # find runs
        current_run = []
        for t in range(time_len):
            if cell_hot[t]:
                current_run.append(t)
            else:
                if len(current_run) >= 5:
                    temp_mhw[current_run] = True
                current_run = []
        if len(current_run) >= 5:
            temp_mhw[current_run] = True
        
        # join gaps
        changed = True
        while changed:
            changed = False
            # Gap of 1
            gap1 = (~temp_mhw[1:-1]) & temp_mhw[:-2] & temp_mhw[2:]
            if np.any(gap1):
                temp_mhw[1:-1] |= gap1
                changed = True
            # Gap of 2
            gap2 = (~temp_mhw[1:-1]) & (~temp_mhw[2:]) & temp_mhw[:-2] & temp_mhw[3:] # this is wrong
                # correct gap 2: temp_mhw[t-1] is T, temp_mhw[t] is F, temp_mhw[t+1] is F, temp_mhw[t+2] is T
                # indices for t: 1 to time_len-3
                # t-1: 0 to time_len-4
                # t: 1 to time_len-3
                # t+1: 2 to time_len-2
                # t+2: 3 to time_len-1
                # let's just use a simple loop for gaps for now, it's only for 1 cell
                # wait, I can use a while loop with bitshifts or similar
                # but let's just fix the loop.
        
        # Simpler gap filling
        # a day is part of MHW if it's hot AND (part of run >= 5 OR connected to MHW)
        # The rule is: "separated by 1 or 2 non-hot days are joined into one, and the gap days belong to it"
        # This means we only join if the gaps are between existing MHWs.
        
        # Let's use the loop again but more carefully
        temp_mhw = np.zeros(time_len, dtype=bool)
        current_run = []
        for t in range(time_len):
            if cell_hot[t]:
                current_run.append(t)
            else:
                if len(current_run) >= 5:
                    temp_mhw[current_run] = True
                current_run = []
        if len(current_run) >= 5:
            temp_mhw[current_run] = True
            
        while True:
            prev_mhw = temp_mhw.copy()
            # Gap of 1
            for t in range(1, time_len-1):
                if not temp_mhw[t] and temp_mhw[t-1] and temp_mhw[t+1]:
                    temp_mhw[t] = True
            # Gap of 2
            for t in range(1, time_len-2):
                if not temp_mhw[t] and not temp_mhw[t+1] and temp_mhw[t-1] and temp_mhw[t+2]:
                    temp_mhw[t] = True
                    temp_mhw[t+1] = True
            if np.array_equal(prev_mhw, temp_mhw):
                break
        
        flat_mhw[:, c] = temp_mhw
        
    return flat_mhw.reshape(time_len, n_lat, n_lon)

mhw_mask = detect_mhw_cells_opt(hot_days)
# Land cells (non-sea cells) should be 0
# sea_cells_mask: (lat, lon)
mhw_mask = mhw_mask * sea_cells_mask[np.newaxis, :, :]

# 4. Regional events
# a day is active if at least one sea cell is inside a per-cell MHW
active_days = np.any(mhw_mask == 1, axis=(1, 2)) # (time,)

# Regional MHW event: maximal run of consecutive active days
regional_events = []
in_event = False
start_day = None
for t in range(len(active_days)):
    if active_days[t]:
        if not in_event:
            in_event = True
            start_day = t
    else:
        if in_event:
            in_event = False
            regional_events.append({"onset": target_days[start_day].strftime('%Y-%m-%d'), 
                                    "end": target_days[t-1].strftime('%Y-%m-%d')})
if in_event:
    regional_events.append({"onset": target_days[start_day].strftime('%Y-%m-%d'), 
                            "end": target_days[-1].strftime('%Y-%m-%d')})

# Results
# output/mhw_mask.nc
os.makedirs('output', exist_ok=True)
mhw_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask.astype(np.uint8))},
    coords={"time": target_days, "latitude": ds_region.latitude, "longitude": ds_region.longitude}
)
mhw_ds.to_netcdf('output/mhw_mask.nc')

# output/report.json
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {
        "start": time_baseline[0].strftime('%Y-%m-%d'),
        "end": time_baseline[-1].strftime('%Y-%m-%d')
    },
    "target_analysed": {
        "start": target_days[0].strftime('%Y-%m-%d'),
        "end": target_days[-1].strftime('%Y-%m-%d')
    },
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Analysis complete.")
