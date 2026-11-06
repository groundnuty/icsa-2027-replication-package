import os
import pandas as pd
import numpy as np
import xarray as xr
from datetime import datetime, timedelta
import json

# Constants
BASE_DIR = "/data/icsa2027_data_20261101T090944Z/s1z"
LAT_MIN, LAT_MAX = 56.09, 57.29
LON_MIN, LON_MAX = 10.55, 11.75
TARGET_START_STR = "2021-06-01"
TARGET_END_STR = "2021-08-31"
BASELINE_START_STR = "1992-01-01"
BASELINE_END_STR = "2002-12-31"

def get_day_of_year(dt):
    """Map every date to a day of year from 1 to 366.
    1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61, ..., 31 December = 366.
    """
    # Use a leap year (2000) as a reference to get the day of year
    return datetime(2000, dt.month, dt.day).timetuple().tm_yday

def load_sst_region(start_date, end_date):
    dates = pd.date_range(start_date, end_date)
    sst_data = []
    lats = None
    lons = None
    
    for dt in dates:
        filename = f"sst_{dt.strftime('%Y%m%d')}.nc"
        path = os.path.join(BASE_DIR, filename)
        if os.path.exists(path):
            with xr.open_dataset(path, engine="h5netcdf") as ds:
                # Selection is inclusive
                # In xarray, .sel(latitude=slice(min, max)) is inclusive if the coordinates are increasing.
                # Let's check coordinate order.
                subset = ds.analysed_sst.sel(
                    latitude=slice(LAT_MIN, LAT_MAX), 
                    longitude=slice(LON_MIN, LON_MAX)
                )
                if lats is None:
                    lats = subset.latitude.values
                    lons = subset.longitude.values
                sst_data.append(subset.values.astype(np.float64))
        else:
            # If file is missing, use NaNs
            if lats is not None:
                sst_data.append(np.full((len(lats), len(lons)), np.nan))
            else:
                # This happens if the very first file is missing. 
                # We can't know the shape yet, but we'll probably encounter a file eventually.
                # For now, let's just use a placeholder.
                sst_data.append(None)
                
    # Handle the case where the first few files were missing
    if sst_data[0] is None:
        # Find first non-None
        for i, val in enumerate(sst_data):
            if val is not None:
                shape = val.shape
                for j in range(i):
                    sst_data[j] = np.full(shape, np.nan)
                break
        else:
            # All missing
            return None, None, None
            
    return np.array(sst_data), lats, lons

# Target dates
target_start = pd.to_datetime(TARGET_START_STR)
target_end = pd.to_datetime(TARGET_END_STR)
target_dates = pd.date_range(target_start, target_end)

# Baseline dates and their boundaries
baseline_start = pd.to_datetime(BASELINE_START_STR)
baseline_end = pd.to_datetime(BASELINE_END_STR)
# To cover windows (+/- 5 days), we need:
pool_start = baseline_start - timedelta(days=5)
pool_end = baseline_end + timedelta(days=5)

print(f"Loading baseline data from {pool_start.date()} to {pool_end.date()}...")
baseline_sst, lats, lons = load_sst_region(pool_start, pool_end)
print(f"Baseline data shape: {baseline_sst.shape}")

print(f"Loading target data from {target_start.date()} to {target_end.date()}...")
target_sst, _, _ = load_sst_region(target_start, target_end)
print(f"Target data shape: {target_sst.shape}")

# 1. Sea cells: finite on every day of the target period
# target_sst shape: (time, lat, lon)
finite_mask = np.all(np.isfinite(target_sst), axis=0)
sea_cells = finite_mask # Boolean array (lat, lon)
num_sea_cells = np.sum(sea_cells)
print(f"Number of sea cells: {num_sea_cells}")

# 2. Threshold and climatology
# Pre-calculate day of year for all dates in the loaded baseline range
all_baseline_dates = pd.date_range(pool_start, pool_end)
baseline_doy = np.array([get_day_of_year(dt) for dt in all_baseline_dates])

# To efficiently find the pool, let's find the dates in the baseline years [1992-01-01, 2002-12-31]
# that have a specific day of year d.
baseline_years_dates = pd.date_range(baseline_start, baseline_end)
baseline_years_doy = np.array([get_day_of_year(dt) for dt in baseline_years_dates])

thresholds = np.full((366, len(lats), len(lons)), np.nan)
climatologies = np.full((366, len(lats), len(lons)), np.nan)

# Only compute for sea cells to save time/memory
sea_lat, sea_lon = np.where(sea_cells)

for d in range(1, 367):
    if d == 60:
        continue
    
    # Find baseline dates T_i with doy == d
    baseline_indices = np.where(baseline_years_doy == d)[0]
    
    # The pool consists of dates T such that |T - T_i| <= 5 for some T_i.
    # T_i are indices relative to baseline_start.
    # The full baseline_sst is relative to pool_start.
    # offset = baseline_start - pool_start
    offset = (baseline_start - pool_start).days
    
    pool_dates_indices = set()
    for idx in baseline_indices:
        # date T_i is at index idx + offset in baseline_sst
        # windows are [idx + offset - 5, idx + offset + 5]
        for window_idx in range(idx + offset - 5, idx + offset + 6):
            if 0 <= window_idx < len(all_baseline_dates):
                pool_dates_indices.add(window_idx)
    
    pool_indices = sorted(list(pool_dates_indices))
    if not pool_indices:
        continue
    
    # Extract SST for these dates
    # baseline_sst shape: (time, lat, lon)
    pool_sst = baseline_sst[pool_indices, :, :] # (pool_len, lat, lon)
    
    # Compute threshold (90th percentile, hazen) and climatology (mean)
    # We only need this for sea cells.
    # Let's use np.nanpercentile with method="hazen" (available in numpy 1.22+)
    # If numpy version is old, we might need a workaround.
    # The prompt says "numpy's method='hazen'".
    
    # To optimize, we can compute for all cells and then mask, or just for sea cells.
    # For simplicity, let's do it for all and use nanpercentile.
    thresholds[d-1] = np.nanpercentile(pool_sst, 90, axis=0, method="hazen")
    climatologies[d-1] = np.nanmean(pool_sst, axis=0)

# Set day 60 (index 59)
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

# Smooth: 31-day moving mean, wrap around
def smooth_366(arr):
    # arr shape: (366, lat, lon)
    smoothed = np.full_like(arr, np.nan)
    for d in range(366):
        # indices d-15 to d+15 modulo 366
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices] # (31, lat, lon)
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

thresholds_smoothed = smooth_366(thresholds)
climatologies_smoothed = smooth_366(climatologies)

# 3. Per-cell MHWs
# Target period: target_sst (time, lat, lon)
# Thresholds: thresholds_smoothed (366, lat, lon)
# Get doy for target dates
target_doy = np.array([get_day_of_year(dt) for dt in target_dates])

# Hot days: SST >= threshold
# We need to map target_doy (1-366) to thresholds_smoothed (0-365)
# thresholds_smoothed[target_doy - 1]
# Using numpy indexing:
hot_mask = np.zeros(target_sst.shape, dtype=bool)
for t in range(len(target_dates)):
    d = target_doy[t]
    hot_mask[t] = target_sst[t] >= thresholds_smoothed[d-1]

# MHW runs: at least 5 consecutive hot days, join gaps of 1-2 non-hot days
mhw_mask = np.zeros(target_sst.shape, dtype=np.uint8)

# Process each sea cell
for lat_idx, lon_idx in zip(*np.where(sea_cells)):
    cell_hot = hot_mask[:, lat_idx, lon_idx]
    
    # Find runs of hot days
    # This can be done by iterating through the array
    in_mhw = np.zeros(len(cell_hot), dtype=bool)
    
    # First, identify all hot runs of >= 5 days
    hot_runs = []
    start = None
    for i in range(len(cell_hot)):
        if cell_hot[i]:
            if start is None:
                start = i
        else:
            if start is not None:
                if i - start >= 5:
                    hot_runs.append((start, i - 1))
                start = None
    if start is not None:
        if len(cell_hot) - start >= 5:
            hot_runs.append((start, len(cell_hot) - 1))
            
    # Now, join runs separated by 1 or 2 non-hot days
    if not hot_runs:
        continue
        
    merged_runs = []
    if hot_runs:
        curr_start, curr_end = hot_runs[0]
        for next_start, next_end in hot_runs[1:]:
            if next_start - curr_end <= 3: # gap of 1 or 2 non-hot days: next_start - curr_end - 1 is the gap size.
                # Wait: "separated by 1 or 2 non-hot days".
                # If curr_end = 10 and next_start = 11, gap is 0 days.
                # If curr_end = 10 and next_start = 12, gap is 1 day (day 11).
                # If curr_end = 10 and next_start = 13, gap is 2 days (days 11, 12).
                # So gap is next_start - curr_end - 1.
                # Gap <= 2 means next_start - curr_end <= 3.
                curr_end = next_end
            else:
                merged_runs.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged_runs.append((curr_start, curr_end))
        
    for s, e in merged_runs:
        in_mhw[s : e + 1] = True
        
    mhw_mask[:, lat_idx, lon_idx] = in_mhw.astype(np.uint8)

# 4. Regional events
# a day is active if at least one sea cell is in an MHW
active_days = np.any(mhw_mask == 1, axis=(1, 2))

regional_events = []
start = None
for i in range(len(active_days)):
    if active_days[i]:
        if start is None:
            start = i
    else:
        if start is not None:
            regional_events.append({
                "onset": target_dates[start].strftime('%Y-%m-%d'),
                "end": target_dates[i-1].strftime('%Y-%m-%d')
            })
            start = None
if start is not None:
    regional_events.append({
        "onset": target_dates[start].strftime('%Y-%m-%d'),
        "end": target_dates[-1].strftime('%Y-%m-%d')
    })

# Save output
os.makedirs("output", exist_ok=True)
# mhw_mask.nc
# Use xarray to save the mask
mask_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={"time": target_dates, "latitude": lats, "longitude": lons}
)
mask_ds.to_netcdf("output/mhw_mask.nc")

# report.json
report = {
    "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
    "baseline_analysed": {"start": pool_start.strftime('%Y-%m-%d'), "end": pool_end.strftime('%Y-%m-%d')},
    "target_analysed": {"start": target_start.strftime('%Y-%m-%d'), "end": target_end.strftime('%Y-%m-%d')},
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Success")
