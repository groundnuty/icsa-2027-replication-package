import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta
import os

# Configuration
LAT_MIN, LAT_MAX = 61.57, 62.77
LON_MIN, LON_MAX = 20.17, 21.37
TARGET_START = "2021-06-01"
TARGET_END = "2021-08-31"
BASELINE_START = "1992-01-01"
BASELINE_END = "2002-12-31"

def get_doy(dt):
    # Map to 1-366 as specified: 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61...
    # This is equivalent to doy in a leap year.
    ref_date = datetime(2000, dt.month, dt.day)
    return (ref_date - datetime(2000, 1, 1)).days + 1

# Load dataset
ds = xr.open_dataset('/work/sst_s2.nc', engine="h5netcdf")
sst = ds['analysed_sst']

# Region slice
sst_reg = sst.sel(latitude=slice(LAT_MIN, LAT_MAX), longitude=slice(LON_MIN, LON_MAX))

# Target period slice
target_sst = sst_reg.sel(time=slice(TARGET_START, TARGET_END))

# Baseline period slice extended by 5 days
baseline_sst = sst_reg.sel(time=slice("1991-12-27", "2003-01-05"))

# 1. Sea cells: SST finite on every day of target period
target_sst_vals = target_sst.values # (time, lat, lon)
is_sea = np.all(np.isfinite(target_sst_vals), axis=0)
sea_indices = np.where(is_sea)

# 2. Threshold and climatology
baseline_times = pd.to_datetime(baseline_sst.time.values)
baseline_sst_vals = baseline_sst.values # (time, lat, lon)
baseline_doys = np.array([get_doy(t.to_pydatetime()) for t in baseline_times])

baseline_range_mask = (baseline_times >= pd.Timestamp(BASELINE_START)) & (baseline_times <= pd.Timestamp(BASELINE_END))
baseline_range_indices = np.where(baseline_range_mask)[0]

thresholds = np.full((366, sst_reg.latitude.size, sst_reg.longitude.size), np.nan, dtype=np.float64)
climatologies = np.full((366, sst_reg.latitude.size, sst_reg.longitude.size), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    
    t_indices = baseline_range_indices[baseline_doys[baseline_range_indices] == d]
    if len(t_indices) == 0:
        continue
    
    mask = np.zeros(len(baseline_times), dtype=bool)
    for t_idx in t_indices:
        t_date = baseline_times[t_idx]
        diffs = np.abs((baseline_times - t_date).days)
        mask |= (diffs <= 5)
    
    pool_vals = baseline_sst_vals[mask]
    thresholds[d-1] = np.nanpercentile(pool_vals, 90, axis=0, method="hazen")
    climatologies[d-1] = np.nanmean(pool_vals, axis=0)

# Day 60
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

def smooth(arr):
    smoothed = np.zeros_like(arr)
    for i in range(366):
        indices = [(i + offset) % 366 for offset in range(-15, 16)]
        window = arr[indices]
        smoothed[i] = np.nanmean(window, axis=0)
    return smoothed

thresholds_smooth = smooth(thresholds)
climatologies_smooth = smooth(climatologies)

# 3. Per-cell MHWs
target_doys = np.array([get_doy(t.to_pydatetime()) for t in pd.to_datetime(target_sst.time.values)])
hot_mask = np.zeros(target_sst_vals.shape, dtype=bool)
for t_idx, d in enumerate(target_doys):
    hot_mask[t_idx] = target_sst_vals[t_idx] >= thresholds_smooth[d-1]

mhw_mask = np.zeros(target_sst_vals.shape, dtype=np.uint8)
for lat_idx, lon_idx in zip(*sea_indices):
    cell_hot = hot_mask[:, lat_idx, lon_idx]
    
    # Find runs of >= 5 hot days
    runs = []
    i = 0
    while i < len(cell_hot):
        if cell_hot[i]:
            start = i
            while i < len(cell_hot) and cell_hot[i]:
                i += 1
            if i - start >= 5:
                runs.append((start, i))
        else:
            i += 1
    
    # Join runs separated by 1 or 2 non-hot days
    if not runs:
        continue
        
    joined_runs = []
    curr_start, curr_end = runs[0]
    for next_start, next_end in runs[1:]:
        gap = next_start - curr_end
        if 1 <= gap <= 2:
            curr_end = next_end
        else:
            joined_runs.append((curr_start, curr_end))
            curr_start, curr_end = next_start, next_end
    joined_runs.append((curr_start, curr_end))
    
    mhw_cell = np.zeros(len(cell_hot), dtype=bool)
    for start, end in joined_runs:
        mhw_cell[start:end] = True
    mhw_mask[:, lat_idx, lon_idx] = mhw_cell.astype(np.uint8)

# 4. Regional events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
i = 0
while i < len(active_days):
    if active_days[i]:
        start = i
        while i < len(active_days) and active_days[i]:
            i += 1
        regional_events.append((start, i - 1))
    else:
        i += 1

# Results
os.makedirs('output', exist_ok=True)
mask_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={"time": target_sst.time, "latitude": sst_reg.latitude, "longitude": sst_reg.longitude}
)
mask_ds.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
    "baseline_analysed": {"start": BASELINE_START, "end": BASELINE_END},
    "target_analysed": {"start": TARGET_START, "end": TARGET_END},
    "events": [
        {
            "onset": pd.to_datetime(target_sst.time.values[start]).strftime('%Y-%m-%d'),
            "end": pd.to_datetime(target_sst.time.values[end]).strftime('%Y-%m-%d')
        }
        for start, end in regional_events
    ],
    "complete": True,
    "caveats": ""
}

with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Successfully wrote output files.")
