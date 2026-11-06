import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

def get_fixed_doy(dt):
    month = dt.month
    day = dt.day
    if month == 1: return day
    if month == 2: return 31 + day
    month_offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_offsets[month-1] + day

# Load region
ds = xr.open_dataset('/work/sst_s2.nc', engine="h5netcdf")
lat_min, lat_max = 59.05, 60.25
lon_min, lon_max = 21.25, 22.45
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Target period
target_start = pd.Timestamp('2014-06-01')
target_end = pd.Timestamp('2014-08-31')
ds_target = ds_region.sel(time=slice(target_start, target_end)).load()

# Sea cells: SST is finite on every day of target period
sst_target = ds_target.analysed_sst.values
# Shape: (time, lat, lon)
finite_mask = np.all(np.isfinite(sst_target), axis=0)
sea_cells_mask = finite_mask

# Baseline period: 1992-01-01 to 2002-12-31
# We need data from 1991-12-27 to 2003-01-05 for the pools
baseline_data_start = pd.Timestamp('1991-12-27')
baseline_data_end = pd.Timestamp('2003-01-05')
ds_baseline_full = ds_region.sel(time=slice(baseline_data_start, baseline_data_end)).load()
sst_baseline = ds_baseline_full.analysed_sst.values
time_baseline = pd.to_datetime(ds_baseline_full.time.values)

# Baseline dates for thresholds: 1992-01-01 to 2002-12-31
baseline_dates = pd.date_range(start='1992-01-01', end='2002-12-31')

# Threshold and Climatology arrays (366, lat, lon)
# Use float64
thresholds = np.full((366, sst_target.shape[1], sst_target.shape[2]), np.nan, dtype=np.float64)
climatologies = np.full((366, sst_target.shape[1], sst_target.shape[2]), np.nan, dtype=np.float64)

# Precompute DOY for all dates in ds_baseline_full
baseline_full_doys = np.array([get_fixed_doy(t) for t in time_baseline])
baseline_full_times = np.array(time_baseline)

# To optimize, let's find which indices in sst_baseline correspond to the windows for each doy
# The pool for doy d: dates within +/- 5 days of any baseline date with doy d.
# 1992-01-01 to 2002-12-31 baseline dates.

for d in range(1, 367):
    if d == 60:
        continue
    
    # Find all dates in [1992-01-01, 2002-12-31] that have DOY d
    # Then find all dates in [1991-12-27, 2003-01-05] that are within 5 days of these.
    
    # Instead of iterating baseline_dates, let's just find all dates in 1992-2002 with DOY d.
    # But we can just iterate through all dates in baseline_full_times and if its DOY is d,
    # mark the window.
    
    # Let's use a boolean mask for the pool
    pool_mask = np.zeros(len(time_baseline), dtype=bool)
    
    # Identify baseline dates (1992-01-01 to 2002-12-31) with DOY d
    # baseline_full_times is already sorted.
    # Find the indices of dates in baseline_full_times that are in [1992-01-01, 2002-12-31]
    # and have DOY == d.
    for i, t in enumerate(time_baseline):
        if pd.Timestamp('1992-01-01') <= t <= pd.Timestamp('2002-12-31'):
            if get_fixed_doy(t) == d:
                # This date is a baseline date with DOY d.
                # Include all dates in baseline_full_times within +/- 5 days.
                # Since baseline_full_times is daily, these are indices [i-5, i+5]
                # but we must be careful about the boundaries of the baseline_full_times array.
                # Wait, the window is calendar days. i-5 to i+5 works if time_baseline is daily.
                start_idx = max(0, i - 5)
                end_idx = min(len(time_baseline) - 1, i + 5)
                # This is actually wrong because baseline_full_times starts from 1991-12-27.
                # 1992-01-01 is index 5. i-5 would be index 0. Correct.
                
                # We need to find indices in time_baseline that are within +/- 5 days of t.
                # Let's just use the indices because it's a daily grid.
                # But wait, if we do this for every date, it's slow.
                # Let's optimize:
                # The window is [t - 5 days, t + 5 days].
                # Since time_baseline is daily, these are exactly the indices i-5 to i+5.
                pool_mask[start_idx : end_idx + 1] = True
                
    # Extract SST values for the pool
    # sst_baseline is (time, lat, lon)
    pool_sst = sst_baseline[pool_mask] # (N, lat, lon)
    
    # Compute 90th percentile and mean along the time axis (0)
    # numpy.nanpercentile(..., method='hazen') for the 90th percentile.
    # Wait, numpy 1.22+ has 'method'. If not, we might need 'interpolation'.
    # "hazen" is available in numpy.quantile since 1.22.0.
    # Let's check numpy version.
    
    # For each cell:
    # thresholds[d-1] = np.nanpercentile(pool_sst, 90, axis=0, method='hazen')
    # climatologies[d-1] = np.nanmean(pool_sst, axis=0)
    
    # To handle NaNs correctly and avoid issues with empty pools:
    if np.any(pool_mask):
        thresholds[d-1] = np.nanpercentile(pool_sst, 90, axis=0, method='hazen')
        climatologies[d-1] = np.nanmean(pool_sst, axis=0)

# Day 60 = mean of 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

# Smoothing: 31-day moving mean, wraps around.
def smooth_366(arr):
    # arr shape: (366, lat, lon)
    smoothed = np.full_like(arr, np.nan)
    for d in range(366):
        # Window: d-15 to d+15 modulo 366
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices] # (31, lat, lon)
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

thresholds_smoothed = smooth_366(thresholds)
climatologies_smoothed = smooth_366(climatologies)

# Now detect MHWs for the target period
# Target SST
sst_target = sst_target.astype(np.float64)
target_times = pd.to_datetime(ds_target.time.values)
target_doys = np.array([get_fixed_doy(t) for t in target_times])

# a day is hot if SST >= threshold for that day
# thresholds_smoothed is (366, lat, lon)
# target_doys is (time,)
# We need thresholds_smoothed[target_doys - 1] which is (time, lat, lon)
thresh_target = thresholds_smoothed[target_doys - 1]
is_hot = sst_target >= thresh_target

# Per-cell MHWs
# - run of at least 5 consecutive hot days
# - separated by 1 or 2 non-hot days are joined
# - target period only

# mhw_mask shape: (time, lat, lon)
mhw_mask = np.zeros_like(is_hot, dtype=np.uint8)

for lat_idx in range(sst_target.shape[1]):
    for lon_idx in range(sst_target.shape[2]):
        hot_days = is_hot[:, lat_idx, lon_idx]
        if not np.any(hot_days):
            continue
        
        # Find runs of hot days
        # This is a 1D array of booleans.
        # Identify MHW segments
        # 1. Find all runs of >= 5 hot days
        # 2. Join them if gap is <= 2
        
        # Use a simple state machine or group by
        # First, find all segments of consecutive hot days
        # Then, find if they are >= 5. If so, mark them.
        # Then, merge those marked segments if gap <= 2.
        
        # Easier:
        # 1. Identify all hot runs.
        # 2. For each run, if length < 5, it's not a seed for MHW.
        # 3. If length >= 5, it's a MHW.
        # 4. Merge MHWs if gap <= 2.
        # 5. But wait, the gap days themselves become part of the MHW.
        
        # Let's use the standard algorithm:
        # a) find all hot runs
        # b) filter runs < 5 days
        # c) merge runs with gaps 1-2 days
        # d) mark all days in merged runs as MHW
        
        runs = []
        start = None
        for i in range(len(hot_days)):
            if hot_days[i]:
                if start is None:
                    start = i
            else:
                if start is not None:
                    runs.append((start, i - 1))
                    start = None
        if start is not None:
            runs.append((start, len(hot_days) - 1))
            
        # Filter runs < 5
        mhw_runs = [r for r in runs if (r[1] - r[0] + 1) >= 5]
        
        # Merge runs
        if not mhw_runs:
            continue
            
        merged = []
        if mhw_runs:
            curr_start, curr_end = mhw_runs[0]
            for i in range(1, len(mhw_runs)):
                next_start, next_end = mhw_runs[i]
                if next_start - curr_end - 1 <= 2:
                    curr_end = next_end
                else:
                    merged.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            merged.append((curr_start, curr_end))
            
        for s, e in merged:
            mhw_mask[s:e+1, lat_idx, lon_idx] = 1

# Regional events
# a day is active if at least one sea cell is in a per-cell MHW
# Note: land cells (not sea cells) are always 0 in mhw_mask.
# Wait, "sea cells are the region's grid cells whose SST is finite on every day of the target period."
# Land cells should be 0.
# Let's make sure only sea cells are considered for active days.
mhw_mask_sea = mhw_mask * sea_cells_mask
active_days = np.any(mhw_mask_sea, axis=(1, 2))

# Regional MHW event: maximal run of consecutive active days
regional_events = []
start = None
for i in range(len(active_days)):
    if active_days[i]:
        if start is None:
            start = i
    else:
        if start is not None:
            regional_events.append((target_times[start].strftime('%Y-%m-%d'), 
                                   target_times[i-1].strftime('%Y-%m-%d')))
            start = None
if start is not None:
    regional_events.append((target_times[start].strftime('%Y-%m-%d'), 
                           target_times[-1].strftime('%Y-%m-%d')))

# Output files
# mhw_mask.nc
ds_out = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask.astype(np.uint8))},
    coords={
        "time": ds_target.time,
        "latitude": ds_region.latitude,
        "longitude": ds_region.longitude,
    },
)
ds_out.to_netcdf("output/mhw_mask.nc")

# report.json
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": "1992-01-01", "end": "2002-12-31"},
    "target_analysed": {"start": target_start.strftime('%Y-%m-%d'), "end": target_end.strftime('%Y-%m-%d')},
    "events": [{"onset": e[0], "end": e[1]} for e in regional_events],
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Success")
