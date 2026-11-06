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
fs = fsspec.filesystem('onedata')
if not os.path.exists(LOCAL_PATH):
    fs.get(REMOTE_PATH, LOCAL_PATH)
ds = xr.open_dataset(LOCAL_PATH, engine='h5netcdf')

# Region slicing
lat_vals = ds.latitude.values
lat_slice = slice(LAT_MAX, LAT_MIN) if lat_vals[0] > lat_vals[-1] else slice(LAT_MIN, LAT_MAX)
ds_region = ds.sel(latitude=lat_slice, longitude=slice(LON_MIN, LON_MAX))

# Use 'analysed_sst' as identified from the previous error
sst = ds_region['analysed_sst'].astype(np.float64)

# --- 1. Sea Cells ---
target_ds = sst.sel(time=slice(TARGET_START, TARGET_END))
is_finite = np.isfinite(target_ds.values).all(axis=0)
sea_sst = sst.where(is_finite)

# --- 2. Threshold and Climatology ---

def get_doy(dt):
    return dt.timetuple().tm_yday

baseline_times = pd.date_range(BASELINE_START, BASELINE_END)
baseline_extended_start = '1991-12-27'
baseline_extended_end = '2003-01-05'
sst_baseline = sea_sst.sel(time=slice(baseline_extended_start, baseline_extended_end))

time_coords = pd.DatetimeIndex(sst_baseline.time.values)
baseline_dates_doy = {t: get_doy(t) for t in baseline_times}

thresholds = np.full((366, *sst.shape[1:]), np.nan, dtype=np.float64)
climatology = np.full((366, *sst.shape[1:]), np.nan, dtype=np.float64)

sst_vals = sst_baseline.values

# Manual implementation of Hyndman-Fan type 5 (hazen) quantile if needed
def hazen_quantile_per_cell(pool, q):
    # pool shape: (num_days, lat, lon)
    # We need to compute the 90th percentile for each (lat, lon) cell
    # np.nanquantile(pool, q, method='hazen') is the ideal.
    # Let's try it; if it fails, we'll fallback.
    try:
        return np.nanquantile(pool, q, method='hazen')
    except (TypeError, ValueError):
        # Fallback: Manual implementation of type 5: q = (i - 0.5) / n
        # i = q * n + 0.5. Index is floor(i-1) and ceil(i-1).
        nlat, nlon = pool.shape[1:]
        res = np.full((nlat, nlon), np.nan)
        for i in range(nlat):
            for j in range(nlon):
                cell = pool[:, i, j]
                valid = cell[~np.isnan(cell)]
                if len(valid) > 0:
                    valid.sort()
                    n = len(valid)
                    idx = q * n + 0.5 - 1 # 0-indexed
                    if idx <= 0:
                        res[i, j] = valid[0]
                    elif idx >= n - 1:
                        res[i, j] = valid[-1]
                    else:
                        # Interpolate
                        low = int(np.floor(idx))
                        high = int(np.ceil(idx))
                        frac = idx - low
                        res[i, j] = valid[low] + frac * (valid[high] - valid[low])
        return res

for d in range(1, 367):
    if d == 60:
        continue
    
    dates_with_doy_d = [t for t, doy in baseline_dates_doy.items() if doy == d]
    all_indices = []
    for t_base in dates_with_doy_d:
        t_base_ts = pd.Timestamp(t_base)
        start_win = t_base_ts - pd.Timedelta(days=5)
        end_win = t_base_ts + pd.Timedelta(days=5)
        idx_start = np.searchsorted(time_coords, start_win)
        idx_end = np.searchsorted(time_coords, end_win, side='right')
        all_indices.extend(range(idx_start, idx_end))
    
    unique_indices = sorted(list(set(all_indices)))
    if not unique_indices:
        continue
        
    pool = sst_vals[unique_indices, :, :]
    thresholds[d-1] = hazen_quantile_per_cell(pool, 0.9)
    climatology[d-1] = np.nanmean(pool, axis=0)

# Day 60 = mean of day 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

def smooth_wrap(arr):
    res = np.full_like(arr, np.nan)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices]
        res[d] = np.nanmean(window, axis=0)
    return res

thresholds_smooth = smooth_wrap(thresholds)
climatology_smooth = smooth_wrap(climatology)

# --- 3. Per-cell MHWs ---
target_sst = sst.sel(time=slice(TARGET_START, TARGET_END)).values
target_times = pd.date_range(TARGET_START, TARGET_END)
target_doys = np.array([get_doy(t) for t in target_times])

hot_days = target_sst >= thresholds_smooth[target_doys - 1]
mhw_mask = np.zeros_like(hot_days, dtype=np.uint8)

num_days, nlat, nlon = hot_days.shape
for i in range(nlat):
    for j in range(nlon):
        cell_hot = hot_days[:, i, j]
        if not np.any(cell_hot):
            continue
        
        # Find runs of at least 5 consecutive hot days
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
        
        if not runs:
            continue
            
        # Join gaps of 1 or 2 non-hot days (gap <= 2 means next_start - curr_end <= 3)
        merged = []
        curr_start, curr_end = runs[0]
        for next_start, next_end in runs[1:]:
            if next_start - curr_end <= 3:
                curr_end = next_end
            else:
                merged.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged.append((curr_start, curr_end))
        
        in_mhw = np.zeros(num_days, dtype=bool)
        for s, e in merged:
            in_mhw[s:e+1] = True
        mhw_mask[:, i, j] = in_mhw.astype(np.uint8)

# --- 4. Regional Events ---
active_days = np.any(mhw_mask == 1, axis=(1, 2))
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

# Save results
ds_mhw = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": target_times,
        "latitude": ds_region.latitude.values,
        "longitude": ds_region.longitude.values
    }
)
ds_mhw.to_netcdf("output/mhw_mask.nc")

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

print("Analysis complete.")
