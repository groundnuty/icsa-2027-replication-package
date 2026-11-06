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
    month_days = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    year = dt.year
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    doy = sum(month_days[:dt.month - 1]) + dt.day
    if is_leap and dt.month > 2:
        doy += 1
    return doy

# 1. Identify and load files
all_files = sorted(glob.glob(os.path.join(DATA_DIR, "sst_*.nc")))

window_start = BASELINE_START - timedelta(days=5)
window_end = BASELINE_END + timedelta(days=5)

baseline_files = []
for f in all_files:
    fname = os.path.basename(f)
    date_str = fname.split('_')[1].replace('.nc', '')
    try:
        dt = datetime.strptime(date_str, "%Y%m%d")
        if window_start <= dt <= window_end:
            baseline_files.append((dt, f))
    except ValueError:
        pass

target_files = []
for f in all_files:
    fname = os.path.basename(f)
    date_str = fname.split('_')[1].replace('.nc', '')
    try:
        dt = datetime.strptime(date_str, "%Y%m%d")
        if TARGET_START <= dt <= TARGET_END:
            target_files.append((dt, f))
    except ValueError:
        pass

baseline_files.sort()
target_files.sort()

def load_region_sst(files_list):
    sst_list = []
    dates = []
    lats = None
    lons = None
    if not files_list:
        return None, None, None, None
    for dt, f in files_list:
        with xr.open_dataset(f, engine="h5netcdf") as ds:
            region_ds = ds.sel(latitude=slice(LAT_MIN, LAT_MAX), longitude=slice(LON_MIN, LON_MAX))
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

n_lat, n_lon = lats.size, lons.size

# 1. Sea cells: SST is finite on every day of the target period
is_sea = np.all(np.isfinite(target_sst), axis=0)

# 2. Threshold and Climatology
thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    
    baseline_indices = []
    for i, (dt, _) in enumerate(baseline_files):
        if BASELINE_START <= dt <= BASELINE_END and get_day_of_year(dt) == d:
            baseline_indices.append(i)
            
    all_window_indices = set()
    for idx in baseline_indices:
        base_date = baseline_dates[idx]
        start_win = base_date - timedelta(days=5)
        end_win = base_date + timedelta(days=5)
        start_pos = np.searchsorted(baseline_dates, start_win)
        end_pos = np.searchsorted(baseline_dates, end_win, side='right')
        for p in range(start_pos, end_pos):
            all_window_indices.add(p)
            
    if all_window_indices:
        pool_indices = sorted(list(all_window_indices))
        pool_data = baseline_sst[pool_indices, :, :]
        thresholds[d-1] = np.nanpercentile(pool_data, 90, axis=0, method="hazen")
        climatology[d-1] = np.nanmean(pool_data, axis=0)

thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

def smooth_366(arr):
    smoothed = np.full_like(arr, np.nan)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices, :, :]
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

thresholds = smooth_366(thresholds)
climatology = smooth_366(climatology)

# 3. Per-cell MHWs
n_target_days = target_sst.shape[0]
hot_days = np.zeros((n_target_days, n_lat, n_lon), dtype=bool)

for i in range(n_target_days):
    doy = get_day_of_year(target_dates[i])
    thresh = thresholds[doy-1]
    hot_days[i] = target_sst[i] >= thresh

mhw_mask = np.zeros((n_target_days, n_lat, n_lon), dtype=np.uint8)

for r in range(n_lat):
    for c in range(n_lon):
        if not is_sea[r, c]:
            continue
            
        cell_hot = hot_days[:, r, c]
        is_mhw = np.zeros(n_target_days, dtype=bool)
        
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
            
        valid_runs = [run for run in runs if (run[1] - run[0] + 1) >= 5]
        if not valid_runs:
            continue
            
        merged_runs = []
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
ds_mask = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={"time": target_dates, "latitude": lats, "longitude": lons}
)
ds_mask.to_netcdf("output/mhw_mask.nc")

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
