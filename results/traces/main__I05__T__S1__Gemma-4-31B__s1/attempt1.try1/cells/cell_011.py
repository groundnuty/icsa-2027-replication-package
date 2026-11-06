import fsspec
import xarray as xr
import numpy as np
import pandas as pd
import json
import os
from datetime import timedelta

# Configuration
lat_min, lat_max = 54.39, 55.59
lon_min, lon_max = 18.25, 19.45
target_start_str = '2021-06-01'
target_end_str = '2021-08-31'
baseline_start_str = '1992-01-01'
baseline_end_str = '2002-12-31'

os.makedirs("output", exist_ok=True)

def get_custom_doy(dt):
    # Custom day of year: 1 Jan = 1, 29 Feb = 60
    days_in_months = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_months[:dt.month]) + dt.day

fs = fsspec.filesystem('onedata')
s2_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(s2_path, "rb") as f:
    # Use chunks to avoid loading the whole 40GB file into memory
    ds = xr.open_dataset(f, engine="h5netcdf", chunks={'time': 500})
    
    # Slice region first
    ds_reg = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    
    # Target period
    target_ds = ds_reg.sel(time=slice(target_start_str, target_end_str))
    target_sst = target_ds['analysed_sst'].astype(np.float64).values
    target_times = target_ds.time.values
    
    # Baseline period with buffers for the ±5 day window
    # Start - 5 days and End + 5 days
    b_start = pd.to_datetime(baseline_start_str)
    b_end = pd.to_datetime(baseline_end_str)
    baseline_ds = ds_reg.sel(time=slice((b_start - timedelta(days=5)).strftime('%Y-%m-%d'), 
                                        (b_end + timedelta(days=5)).strftime('%Y-%m-%d')))
    baseline_sst = baseline_ds['analysed_sst'].astype(np.float64).values
    baseline_times = baseline_ds.time.values

# 1. Sea cells
# Sea cells are finite on every day of the target period
is_finite = np.all(np.isfinite(target_sst), axis=0)
sea_cells = is_finite

# 2. Threshold and Climatology
b_times_dt = pd.to_datetime(baseline_times)
b_doys = np.array([get_custom_doy(t) for t in b_times_dt])

# Baseline baseline years only: 1992-01-01 to 2002-12-31
b_range_mask = (b_times_dt >= b_start) & (b_times_dt <= b_end)
b_indices = np.where(b_range_mask)[0]

thresholds = np.full((367, *sea_cells.shape), np.nan, dtype=np.float64)
climatology = np.full((367, *sea_cells.shape), np.nan, dtype=np.float64)

# Map doy to baseline dates (indices in baseline_sst)
doy_to_idx = {}
for idx in b_indices:
    d = b_doys[idx]
    if d not in doy_to_idx:
        doy_to_idx[d] = []
    doy_to_idx[d].append(idx)

for d in range(1, 367):
    if d == 60: continue
    if d not in doy_to_idx: continue
    
    pool_indices = set()
    for t_idx in doy_to_idx[d]:
        for offset in range(-5, 6):
            idx = t_idx + offset
            if 0 <= idx < len(baseline_sst):
                pool_indices.add(idx)
    
    pool = baseline_sst[sorted(list(pool_indices)), :, :]
    thresholds[d] = np.nanpercentile(pool, 90, axis=0, method="hazen")
    climatology[d] = np.nanmean(pool, axis=0)

# Handle day 60
thresholds[60] = (thresholds[59] + thresholds[61]) / 2
climatology[60] = (climatology[59] + climatology[61]) / 2

def smooth_array(arr):
    data = arr[1:] # 1 to 366
    smoothed = np.full_like(data, np.nan)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = data[indices, :, :]
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

smoothed_thresholds = smooth_array(thresholds)

# 3. Per-cell MHWs
t_times_dt = pd.to_datetime(target_times)
t_doys = np.array([get_custom_doy(t) for t in t_times_dt])
t_doy_indices = t_doys - 1

t_thresholds = smoothed_thresholds[t_doy_indices]
is_hot = target_sst >= t_thresholds

mhw_mask = np.zeros_like(is_hot, dtype=np.uint8)

def find_mhw_indices(hot_series):
    n = len(hot_series)
    mhw = np.zeros(n, dtype=bool)
    runs = []
    start = None
    for i in range(n):
        if hot_series[i]:
            if start is None: start = i
        else:
            if start is not None:
                if i - start >= 5: runs.append((start, i - 1))
                start = None
    if start is not None and n - start >= 5:
        runs.append((start, n - 1))
    
    if not runs: return mhw
    
    joined = []
    cs, ce = runs[0]
    for ns, ne in runs[1:]:
        if ns - ce - 1 <= 2:
            ce = ne
        else:
            joined.append((cs, ce))
            cs, ce = ns, ne
    joined.append((cs, ce))
    
    for s, e in joined:
        mhw[s : e + 1] = True
    return mhw

# Process only sea cells
for r in range(sea_cells.shape[0]):
    for c in range(sea_cells.shape[1]):
        if sea_cells[r, c]:
            mhw_mask[:, r, c] = find_mhw_indices(is_hot[:, r, c])

# 4. Regional Events
is_active = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
start = None
for i in range(len(is_active)):
    if is_active[i]:
        if start is None: start = i
    else:
        if start is not None:
            regional_events.append((t_times_dt[start], t_times_dt[i-1]))
            start = None
if start is not None:
    regional_events.append((t_times_dt[start], t_times_dt[-1]))

# Output
ds_out = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": target_times,
        "latitude": ds_reg.latitude.values,
        "longitude": ds_reg.longitude.values,
    },
)
ds_out.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {
        "start": (b_start - timedelta(days=5)).strftime("%Y-%m-%d"),
        "end": (b_end + timedelta(days=5)).strftime("%Y-%m-%d")
    },
    "target_analysed": {
        "start": target_start_str,
        "end": target_end_str
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

print("Success")
