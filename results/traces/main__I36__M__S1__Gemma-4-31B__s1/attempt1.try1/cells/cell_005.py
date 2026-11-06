import os
import glob
import pandas as pd
import numpy as np
import xarray as xr
from datetime import datetime, timedelta
import json

# Constants
LAT_MIN, LAT_MAX = 60.09, 61.29
LON_MIN, LON_MAX = 20.01, 21.21
BASELINE_START = datetime(1992, 1, 1)
BASELINE_END = datetime(2002, 12, 31)
TARGET_START = datetime(2003, 6, 1)
TARGET_END = datetime(2003, 8, 31)

DATA_DIR = "/data/icsa2027_data_20261101T090944Z/s1z"

def get_day_of_year(dt):
    """Map date to day of year 1-366. Non-leap years have no day 60."""
    # Month days for non-leap year
    month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    # Check if leap year
    year = dt.year
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    
    # Calculate day of year
    doy = sum(month_days[:dt.month - 1]) + dt.day
    if is_leap and dt.month > 2:
        doy += 1
    
    # If it's Feb 29, doy will be 60
    return doy

def get_doy_adjusted(dt):
    """Used for identifying baseline dates. Returns doy 1-366.
    For Feb 29, it's 60."""
    # This is actually just the standard Julian day
    return dt.timetuple().tm_yday

# 1. Identify and load files
all_files = sorted(glob.glob(os.path.join(DATA_DIR, "sst_*.nc")))

# Baseline window range: BASELINE_START - 5 days to BASELINE_END + 5 days
window_start = BASELINE_START - timedelta(days=5)
window_end = BASELINE_END + timedelta(days=5)

baseline_files = []
for f in all_files:
    fname = os.path.basename(f)
    date_str = fname.split('_')[1].replace('.nc', '')
    dt = datetime.strptime(date_str, "%Y%m%d")
    if window_start <= dt <= window_end:
        baseline_files.append((dt, f))

target_files = []
for f in all_files:
    fname = os.path.basename(f)
    date_str = fname.split('_')[1].replace('.nc', '')
    dt = datetime.strptime(date_str, "%Y%m%d")
    if TARGET_START <= dt <= TARGET_END:
        target_files.append((dt, f))

# Sort by date
baseline_files.sort()
target_files.sort()

# Extract SST for the region
def load_region_sst(files_list):
    sst_list = []
    dates = []
    lats = None
    lons = None
    
    if not files_list:
        return None, None, None, None
        
    for dt, f in files_list:
        with xr.open_dataset(f, engine="h5netcdf") as ds:
            # Slice region
            region_ds = ds.sel(latitude=slice(LAT_MIN, LAT_MAX), longitude=slice(LON_MIN, LON_MAX))
            # Handle if sliced result is empty
            if region_ds.latitude.size == 0 or region_ds.longitude.size == 0:
                # The slice might be empty if the coordinates are not perfectly aligned
                # Try to use nearest or just check boundaries
                pass
            
            # Use explicit slicing if slice() is tricky with float bounds
            # But sel with slice should work for coordinates
            
            sst = region_ds.analysed_sst.values.astype(np.float64)
            sst_list.append(sst)
            dates.append(dt)
            if lats is None:
                lats = region_ds.latitude.values
                lons = region_ds.longitude.values
                
    return np.array(sst_list), np.array(dates), lats, lons

print("Loading baseline data...")
baseline_sst, baseline_dates, lats, lons = load_region_sst(baseline_files)
print("Loading target data...")
target_sst, target_dates, _, _ = load_region_sst(target_files)

# Shape of sst: (time, lat, lon)
n_lat, n_lon = lats.size, lons.size

# 2. Threshold and Climatology
# thresholds and climatology will be (366, lat, lon)
thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

# We need a fast way to get SST values for a window
# Create a mapping from date to index in baseline_sst
date_to_idx = {d: i for i, d in enumerate(baseline_dates)}

# Iterate through each day of year d (1-366) except 60
for d in range(1, 367):
    if d == 60:
        continue
    
    # Pool for day d
    pool = []
    # For each baseline year (1992-2002)
    for year in range(1992, 2003):
        # Find the date in this year that has day of year d
        # Note: If year is not leap and d=60, it doesn't exist. 
        # But we're skipping d=60.
        # How to find the date for a given doy d in year 'year'?
        # We can iterate through all dates in baseline_dates and check.
        # Actually, we can just pre-calculate the doy for all baseline_dates.
        pass

# Let's refine the pool logic
baseline_doys = np.array([get_day_of_year(d) for d in baseline_dates])

for d in range(1, 367):
    if d == 60:
        continue
    
    # Find all baseline dates that are "baseline dates whose day of year is d"
    # Baseline dates are 1992-01-01 to 2002-12-31
    baseline_indices = []
    for i, (dt, _) in enumerate(baseline_files):
        if BASELINE_START <= dt <= BASELINE_END and get_day_of_year(dt) == d:
            baseline_indices.append(i)
            
    # For each such date, get the window ± 5 days
    # we want all SST values from dates in [date - 5, date + 5]
    # We can find these dates in our baseline_dates array.
    
    all_window_indices = set()
    for idx in baseline_indices:
        base_date = baseline_dates[idx]
        start_win = base_date - timedelta(days=5)
        end_win = base_date + timedelta(days=5)
        # Find indices of dates in this window
        # Since baseline_dates is sorted, we can use searchsorted
        start_pos = np.searchsorted(baseline_dates, start_win)
        end_pos = np.searchsorted(baseline_dates, end_win, side='right')
        for p in range(start_pos, end_pos):
            all_window_indices.add(p)
            
    # Collect SST values for these indices
    if all_window_indices:
        pool_indices = sorted(list(all_window_indices))
        pool_data = baseline_sst[pool_indices, :, :] # (n_days, n_lat, n_lon)
        
        # Threshold: 90th percentile (hazen), ignoring NaN
        # Climatology: Mean, ignoring NaN
        # np.nanpercentile is slow, we might need a loop or a better way
        # Since we need it per cell, we can use nanpercentile along axis 0
        thresholds[d-1] = np.nanpercentile(pool_data, 90, axis=0, method="hazen")
        climatology[d-1] = np.nanmean(pool_data, axis=0)

# Day 60 = mean of 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

# Smoothing: 31-day moving mean, centered, wrap around
def smooth_366(arr):
    # arr: (366, lat, lon)
    smoothed = np.full_like(arr, np.nan)
    for d in range(366):
        # indices d-15 ... d+15
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices, :, :]
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

thresholds = smooth_366(thresholds)
climatology = smooth_366(climatology)

# 3. Per-cell MHWs
# Target period: 2003-06-01 to 2003-08-31
# SST: (n_target_days, n_lat, n_lon)
# target_dates: sorted array of datetime
n_target_days = target_sst.shape[0]
hot_days = np.zeros((n_target_days, n_lat, n_lon), dtype=bool)

for i in range(n_target_days):
    doy = get_day_of_year(target_dates[i])
    # Threshold for this doy (index doy-1)
    thresh = thresholds[doy-1]
    hot_days[i] = target_sst[i] >= thresh

# Per-cell MHW: run of >= 5 consecutive hot days, gaps of 1-2 days joined
mhw_mask = np.zeros((n_target_days, n_lat, n_lon), dtype=np.uint8)

for r in range(n_lat):
    for c in range(n_lon):
        # cell_hot: boolean array of length n_target_days
        cell_hot = hot_days[:, r, c]
        
        # Find runs of hot days
        is_mhw = np.zeros(n_target_days, dtype=bool)
        
        # Simple algorithm to find MHWs:
        # 1. Identify all runs of consecutive hot days
        # 2. Keep only those with length >= 5
        # 3. Join those separated by 1 or 2 non-hot days
        
        # First pass: find all hot runs and their lengths
        runs = []
        start = None
        for i in range(n_target_days):
            if cell_hot[i]:
                if start is None:
                    start = i
            else:
                if start is not None:
                    runs.append((start, i - 1))
                    start = None
        if start is not None:
            runs.append((start, n_target_days - 1))
            
        # Keep runs >= 5 days
        valid_runs = [run for run in runs if (run[1] - run[0] + 1) >= 5]
        
        if not valid_runs:
            continue
            
        # Join runs separated by 1 or 2 days
        merged_runs = []
        if valid_runs:
            curr_start, curr_end = valid_runs[0]
            for next_start, next_end in valid_runs[1:]:
                if next_start - curr_end - 1 <= 2:
                    curr_end = next_end
                else:
                    merged_runs.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            merged_runs.append((curr_start, curr_end))
            
        for s, e in merged_runs:
            is_mhw[s : e+1] = True
            
        mhw_mask[:, r, c] = is_mhw.astype(np.uint8)

# 4. Regional Events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
start = None
for i in range(n_target_days):
    if active_days[i]:
        if start is None:
            start = i
    else:
        if start is not None:
            regional_events.append((target_dates[start], target_dates[i-1]))
            start = None
if start is not None:
    regional_events.append((target_dates[start], target_dates[n_target_days-1]))

# Write output
os.makedirs("output", exist_ok=True)

# mhw_mask.nc
ds_mask = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={"time": target_dates, "latitude": lats, "longitude": lons}
)
ds_mask.to_netcdf("output/mhw_mask.nc")

# report.json
report = {
    "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
    "baseline_analysed": {
        "start": baseline_dates[0].strftime("%Y-%m-%d") if len(baseline_dates) > 0 else None,
        "end": baseline_dates[-1].strftime("%Y-%m-%d") if len(baseline_dates) > 0 else None
    },
    "target_analysed": {
        "start": target_dates[0].strftime("%Y-%m-%d") if len(target_dates) > 0 else None,
        "end": target_dates[-1].strftime("%Y-%m-%d") if len(target_dates) > 0 else None
    },
    "events": [
        {"onset": e[0].strftime("%Y-%m-%d"), "end": e[1].strftime("%Y-%m-%d")} 
        for e in regional_events
    ],
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Done.")
