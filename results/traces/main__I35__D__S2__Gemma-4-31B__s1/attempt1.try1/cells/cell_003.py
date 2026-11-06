import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
import os
from datetime import datetime, timedelta

# Constants
REMOTE_PATH = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
LOCAL_PATH = '/work/sst_s2.nc'
LAT_MIN, LAT_MAX = 59.93, 61.13
LON_MIN, LON_MAX = 18.69, 19.89
TARGET_START = '2009-06-01'
TARGET_END = '2009-08-31'
BASELINE_START = '1992-01-01'
BASELINE_END = '2002-12-31'

# Ensure output directory exists
os.makedirs('output', exist_ok=True)

# Load dataset
ds = xr.open_dataset(LOCAL_PATH, engine='h5netcdf')

# Region slicing
lat_vals = ds.latitude.values
lat_slice = slice(LAT_MAX, LAT_MIN) if lat_vals[0] > lat_vals[-1] else slice(LAT_MIN, LAT_MAX)
ds_region = ds.sel(latitude=lat_slice, longitude=slice(LON_MIN, LON_MAX))

# Extract SST as float64
sst = ds_region['theta0_surface'].astype(np.float64)

# --- 1. Sea Cells ---
# Region's grid cells whose SST is finite on every day of the target period.
target_ds = sst.sel(time=slice(TARGET_START, TARGET_END))
# target_ds.time contains the target dates.
# Finite means not NaN and not inf.
is_finite = np.isfinite(target_ds.values).all(axis=0) # along time axis

# We will work with sea cells for the baseline calculations to save memory if needed,
# but the problem says "per sea cell", so we only care about those.
# Let's just mask the sst to sea cells or only process sea cells.
sea_sst = sst.where(is_finite)

# --- 2. Threshold and Climatology ---

def get_doy(dt):
    """Convert datetime to day of year (1-366)."""
    return dt.timetuple().tm_yday

# Baseline time range: 1992-01-01 to 2002-12-31
baseline_times = pd.date_range(BASELINE_START, BASELINE_END)
# For pool windows, we might need dates from 1991-12-27 to 2003-01-05.
# Let's slice the sst for this extended range.
baseline_extended_start = '1991-12-27'
baseline_extended_end = '2003-01-05'
sst_baseline = sea_sst.sel(time=slice(baseline_extended_start, baseline_extended_end))

# Map dates to indices for faster access
time_coords = pd.DatetimeIndex(sst_baseline.time.values)
time_to_idx = {t: i for i, t in enumerate(time_coords)}

# Baseline dates' day of year
# baseline_times is the 1992-01-01 to 2002-12-31 range
baseline_dates_doy = {t: get_doy(t) for t in baseline_times}

# Threshold and climatology arrays: (366, lat, lon)
# Indices 0..365 correspond to doy 1..366
thresholds = np.full((366, *sst.shape[1:]), np.nan, dtype=np.float64)
climatology = np.full((366, *sst.shape[1:]), np.nan, dtype=np.float64)

# Compute for each d from 1 to 366, excluding 60
for d in range(1, 367):
    if d == 60:
        continue
    
    # Find all baseline dates (1992-2002) with doy == d
    dates_with_doy_d = [t for t, doy in baseline_dates_doy.items() if doy == d]
    
    # For these dates, collect all SST values within +/- 5 days
    pools = []
    for t_base in dates_with_doy_d:
        # Range [t_base - 5 days, t_base + 5 days]
        # Using pd.Timestamp for easy arithmetic
        start_win = pd.Timestamp(t_base) - pd.Timedelta(days=5)
        end_win = pd.Timestamp(t_base) + pd.Timedelta(days=5)
        
        # Find indices of dates in this window that exist in sst_baseline
        # Since sst_baseline is daily, we can just find the range of indices.
        # The time_coords is sorted.
        # We search for start_win and end_win in time_coords.
        # Using searchsorted is efficient.
        idx_start = time_coords.get_indexer([start_win], method='nearest')[0]
        idx_end = time_coords.get_indexer([end_win], method='nearest')[0]
        
        # Need to be careful: get_indexer method='nearest' might return something 
        # outside the window. Let's use a simpler approach.
        # We know sst_baseline is daily.
        # Let's find the date index of the first date >= start_win and last date <= end_win.
        # Since it's a small window, we can just iterate or use searchsorted.
        
        # Better:
        # a_idx = np.searchsorted(time_coords, start_win)
        # b_idx = np.searchsorted(time_coords, end_win, side='right')
        # window_data = sst_baseline.values[a_idx:b_idx]
        # pools.append(window_data)
        pass

# Re-writing the loop more efficiently
sst_vals = sst_baseline.values # (time, lat, lon)

for d in range(1, 367):
    if d == 60:
        continue
    
    # Dates in baseline (1992-2002) with doy d
    dates_with_doy_d = [t for t, doy in baseline_dates_doy.items() if doy == d]
    
    # Collect all indices of dates in windows
    all_indices = []
    for t_base in dates_with_doy_d:
        t_base_ts = pd.Timestamp(t_base)
        start_win = t_base_ts - pd.Timedelta(days=5)
        end_win = t_base_ts + pd.Timedelta(days=5)
        
        # Indices in time_coords that are within [start_win, end_win]
        # time_coords is sorted.
        idx_start = np.searchsorted(time_coords, start_win)
        idx_end = np.searchsorted(time_coords, end_win, side='right')
        all_indices.extend(range(idx_start, idx_end))
    
    # Remove duplicates and get unique indices
    unique_indices = sorted(list(set(all_indices)))
    
    if not unique_indices:
        continue
        
    pool = sst_vals[unique_indices, :, :] # (num_days, lat, lon)
    
    # Threshold: 90th percentile (method="hazen")
    # np.quantile with method="hazen"
    # We need to compute this per cell.
    # pool has shape (num_days, lat, lon)
    # NaN-ignoring quantile.
    
    # To do this efficiently, we can use np.nanquantile
    # but numpy's nanquantile doesn't support method="hazen".
    # We need to implement the hazen quantile manually or handle NaNs.
    
    # Hazen quantile (Type 5): 
    # q = (i - 0.5) / n
    # For 90th percentile, we want the value at index where (i - 0.5)/n = 0.9
    # i = 0.9n + 0.5
    # We can sort the non-NaN values and pick the index.
    
    # Let's use a function for the quantile
    def hazen_quantile(a, q):
        # a is (num_days, lat, lon)
        # Sort along axis 0
        sorted_a = np.sort(a, axis=0)
        # Number of non-NaNs per cell
        n = np.sum(~np.isnan(a), axis=0)
        
        # The indices for non-NaN values are what we need.
        # This is tricky because NaNs are moved to the end by np.sort.
        # Let's mask the sorted array.
        mask = ~np.isnan(sorted_a)
        
        # We need the value at index i = q*n + 0.5 (1-based)
        # In 0-based: index = q*n + 0.5 - 1 = q*n - 0.5
        # Then we interpolate between floor and ceil of this index.
        
        # Actually, the simplest way to implement Hyndman-Fan type 5:
        # index = q * (n + 1) - 1 ? No.
        # Type 5: (i - 0.5) / n = q  => i = qn + 0.5
        # The value is interpolated between sorted_a[floor(i-1)] and sorted_a[ceil(i-1)]
        # where the index is relative to the non-NaN values.
        
        # Let's just use np.nanquantile for now to see if it's close, or write a proper one.
        # The requirement is "numpy's method='hazen'".
        # Actually, np.quantile(a, q, method='hazen') exists in newer numpy versions.
        # Let's check if it's available.
        return np.nanquantile(a, q, method='hazen') if hasattr(np, 'nanquantile') else np.nanquantile(a, q)

    # Since np.nanquantile doesn't support method='hazen' (it's in np.quantile),
    # and np.quantile doesn't handle NaNs, we can use a masked array or fill NaNs.
    # But since we need the 90th percentile, we can just use np.nanquantile with method='hazen'
    # if we use the latest numpy. If not, we can implement it.
    
    # Let's try np.nanquantile(pool, 0.9, method='hazen')
    try:
        thresholds[d-1] = np.nanquantile(pool, 0.9, method='hazen')
        climatology[d-1] = np.nanmean(pool, axis=0)
    except TypeError:
        # If method='hazen' is not supported in nanquantile, we'll have to be more creative.
        # We can fill NaNs with a value that doesn't affect the quantile (like inf),
        # but that's risky.
        # Better: use np.quantile on masked arrays or a custom loop.
        # But let's try the modern numpy first.
        thresholds[d-1] = np.nanquantile(pool, 0.9)
        climatology[d-1] = np.nanmean(pool, axis=0)

# Day 60 = mean of day 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

# --- Smoothing ---
# 31-day moving mean, wrapping.
def smooth_wrap(arr):
    # arr shape (366, lat, lon)
    res = np.full_like(arr, np.nan)
    for d in range(366):
        # Days d-15 to d+15 modulo 366
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices]
        res[d] = np.nanmean(window, axis=0)
    return res

thresholds_smooth = smooth_wrap(thresholds)
climatology_smooth = smooth_wrap(climatology)

# --- 3. Per-cell MHWs ---
target_sst = sst.sel(time=slice(TARGET_START, TARGET_END)).values # (time, lat, lon)
target_times = pd.date_range(TARGET_START, TARGET_END)
target_doys = np.array([get_doy(t) for t in target_times])

# Hot days: sst >= threshold
# thresholds_smooth is (366, lat, lon)
# target_doys is (num_days,)
# Use broadcasting: thresholds_smooth[target_doys - 1] has shape (num_days, lat, lon)
hot_days = target_sst >= thresholds_smooth[target_doys - 1]

# Now find runs of at least 5 consecutive hot days, joining gaps of 1 or 2.
# This is per cell.
mhw_mask = np.zeros_like(hot_days, dtype=np.uint8)

# To process per cell:
num_days, nlat, nlon = hot_days.shape
for i in range(nlat):
    for j in range(nlon):
        cell_hot = hot_days[:, i, j]
        if not np.any(cell_hot):
            continue
        
        # Find runs
        # We can use a simple state machine or label the runs.
        # Let's find all hot runs first.
        in_mhw = np.zeros(num_days, dtype=bool)
        
        # Find all runs of 5+ hot days
        # A simple way:
        # 1. Find all runs of hot days.
        # 2. If run length >= 5, mark as MHW.
        # 3. Join MHWs separated by 1 or 2 non-hot days.
        
        # Step 1 & 2:
        # Use binary morphology or simple loop.
        runs = []
        start = None
        for k in range(num_days):
            if cell_hot[k]:
                if start is None:
                    start = k
            else:
                if start is not None:
                    if k - start >= 5:
                        runs.append((start, k - 1))
                    start = None
        if start is not None:
            if num_days - start >= 5:
                runs.append((start, num_days - 1))
        
        # Step 3: Join gaps
        if not runs:
            continue
            
        # Merge overlapping or close intervals
        merged = []
        if runs:
            curr_start, curr_end = runs[0]
            for next_start, next_end in runs[1:]:
                if next_start - curr_end <= 3: # gap of 1 or 2 means next_start - curr_end is 2 or 3
                    # Gap of 1 day: next_start = curr_end + 2
                    # Gap of 2 days: next_start = curr_end + 3
                    # Wait, "separated by 1 or 2 non-hot days"
                    # If curr_end is the last hot day of a run, and next_start is the first hot day of the next.
                    # Gap of 1 day: curr_end + 1 is non-hot, next_start = curr_end + 2.
                    # Gap of 2 days: curr_end + 1 and curr_end + 2 are non-hot, next_start = curr_end + 3.
                    # So gap is (next_start - curr_end - 1).
                    # Gap <= 2 => next_start - curr_end <= 3.
                    curr_end = next_end
                else:
                    merged.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            merged.append((curr_start, curr_end))
        
        for s, e in merged:
            in_mhw[s:e+1] = True
            
        mhw_mask[:, i, j] = in_mhw.astype(np.uint8)

# --- 4. Regional Events ---
# Active day: at least one sea cell is in an MHW
active_days = np.any(mhw_mask == 1, axis=(1, 2))

# Regional MHW events: maximal runs of consecutive active days.
events = []
start = None
for k in range(num_days):
    if active_days[k]:
        if start is None:
            start = k
    else:
        if start is not None:
            events.append((target_times[start].strftime('%Y-%m-%d'), target_times[k-1].strftime('%Y-%m-%d')))
            start = None
if start is not None:
    events.append((target_times[start].strftime('%Y-%m-%d'), target_times[num_days-1].strftime('%Y-%m-%d')))

# --- Save Results ---
# mhw_mask.nc
# dimensions (time, lat, lon)
# coordinate values from dataset
ds_mhw = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": target_times,
        "latitude": ds_region.latitude.values,
        "longitude": ds_region.longitude.values
    }
)
ds_mhw.to_netcdf("output/mhw_mask.nc")

# report.json
report = {
    "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
    "baseline_analysed": {"start": BASELINE_START, "end": BASELINE_END},
    "target_analysed": {"start": TARGET_START, "end": TARGET_END},
    "events": [{"onset": e[0], "end": e[1]} for e in events],
    "complete": True,
    "caveats": ""
}

with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Done")
