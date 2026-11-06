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
    if not (fname.startswith("sst_") and fname.endswith(".nc")): continue
    try:
        dt = datetime.strptime(fname[4:-3], "%Y%m%d")
        if window_start <= dt <= window_end:
            baseline_files.append((dt, f))
    except ValueError: pass
baseline_files.sort()

target_files = []
for f in all_files:
    fname = os.path.basename(f)
    if not (fname.startswith("sst_") and fname.endswith(".nc")): continue
    try:
        dt = datetime.strptime(fname[4:-3], "%Y%m%d")
        if TARGET_START <= dt <= TARGET_END:
            target_files.append((dt, f))
    except ValueError: pass
target_files.sort()

def load_region_sst(files_list):
    if not files_list: return None, None, None, None
    sst_list, dates, lats, lons = [], [], None, None
    for dt, f in files_list:
        with xr.open_dataset(f, engine="h5netcdf") as ds:
            region_ds = ds.sel(latitude=slice(LAT_MIN, LAT_MAX), longitude=slice(LON_MIN, LON_MAX))
            sst = region_ds.analysed_sst.values.astype(np.float64)
            sst_list.append(sst)
            dates.append(dt)
            if lats is None:
                lats, lons = region_ds.latitude.values, region_ds.longitude.values
    return np.array(sst_list), np.array(dates), lats, lons

print("Loading data...")
baseline_sst, baseline_dates, lats, lons = load_region_sst(baseline_files)
target_sst, target_dates, _, _ = load_region_sst(target_files)

if target_sst is None:
    # Handle empty target
    os.makedirs("output", exist_ok=True)
    xr.Dataset({"mhw": (("time", "latitude", "longitude"), np.array([], dtype=np.uint8))}, 
               coords={"time": np.array([], dtype='datetime64[ns]'), "latitude": np.array([]), "longitude": np.array([])}).to_netcdf("output/mhw_mask.nc")
    with open("output/report.json", "w") as f:
        json.dump({"region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX}, "baseline_analysed": None, "target_analysed": None, "events": [], "complete": True, "caveats": "No target data"}, f)
    print("Done (no data).")
    exit()

n_lat, n_lon = lats.size, lons.size
is_sea = np.all(np.isfinite(target_sst), axis=0)

# 2. Threshold and Climatology
thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60: continue
    baseline_indices = [i for i, (dt, _) in enumerate(baseline_files) if BASELINE_START <= dt <= BASELINE_END and get_day_of_year(dt) == d]
    all_win_idx = set()
    for idx in baseline_indices:
        base_dt = baseline_dates[idx]
        s_pos = np.searchsorted(baseline_dates, base_dt - timedelta(days=5))
        e_pos = np.searchsorted(baseline_dates, base_dt + timedelta(days=5), side='right')
        all_win_idx.update(range(s_pos, e_pos))
    if all_win_idx:
        pool = baseline_sst[sorted(list(all_win_idx)), :, :]
        thresholds[d-1] = np.nanpercentile(pool, 90, axis=0, method="hazen")
        climatology[d-1] = np.nanmean(pool, axis=0)

thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

def smooth_366(arr):
    sm = np.full_like(arr, np.nan)
    for d in range(366):
        idx = [(d + i) % 366 for i in range(-15, 16)]
        sm[d] = np.nanmean(arr[idx, :, :], axis=0)
    return sm

thresholds = smooth_366(thresholds)
climatology = smooth_366(climatology)

# 3. Per-cell MHWs
n_target_days = target_sst.shape[0]
mhw_mask = np.zeros((n_target_days, n_lat, n_lon), dtype=np.uint8)

for r in range(n_lat):
    for c in range(n_lon):
        if not bool(is_sea[r, c]): continue
        cell_sst = target_sst[:, r, c]
        cell_thresh = np.array([thresholds[get_day_of_year(dt)-1] for dt in target_dates])
        #Wait, thresholds is (366, lat, lon), so thresholds[doy-1, r, c]
        #Correcting:
        cell_thresh = np.array([thresholds[get_day_of_year(dt)-1, r, c] for dt in target_dates])
        
        hot = cell_sst >= cell_thresh
        is_mhw = np.zeros(n_target_days, dtype=bool)
        
        runs = []
        start = None
        for i in range(n_target_days):
            if hot[i]:
                if start is None: start = i
            else:
                if start is not None:
                    runs.append((start, i-1))
                    start = None
        if start is not None: runs.append((start, n_target_days-1))
        
        valid_runs = [run for run in runs if (run[1] - run[0] + 1) >= 5]
        if len(valid_runs) > 0:
            merged = []
            curr_s, curr_e = valid_runs[0]
            for next_s, next_e in valid_runs[1:]:
                if next_s - curr_e - 1 <= 2:
                    curr_e = next_e
                else:
                    merged.append((curr_s, curr_e))
                    curr_s, curr_e = next_s, next_e
            merged.append((curr_s, curr_e))
            for s, e in merged:
                is_mhw[s : e+1] = True
        mhw_mask[:, r, c] = is_mhw.astype(np.uint8)

# 4. Regional Events
active = np.any(mhw_mask == 1, axis=(1, 2))
events = []
start = None
for i in range(n_target_days):
    if active[i]:
        if start is None: start = i
    else:
        if start is not None:
            events.append({"onset": target_dates[start].strftime("%Y-%m-%d"), "end": target_dates[i-1].strftime("%Y-%m-%d")})
            start = None
if start is not None:
    events.append({"onset": target_dates[start].strftime("%Y-%m-%d"), "end": target_dates[n_target_days-1].strftime("%Y-%m-%d")})

# Write output
os.makedirs("output", exist_ok=True)
xr.Dataset({"mhw": (("time", "latitude", "longitude"), mhw_mask)}, 
           coords={"time": target_dates, "latitude": lats, "longitude": lons}).to_netcdf("output/mhw_mask.nc")
with open("output/report.json", "w") as f:
    json.dump({"region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX}, 
               "baseline_analysed": {"start": baseline_dates[0].strftime("%Y-%m-%d"), "end": baseline_dates[-1].strftime("%Y-%m-%d")},
               "target_analysed": {"start": target_dates[0].strftime("%Y-%m-%d"), "end": target_dates[-1].strftime("%Y-%m-%d")},
               "events": events, "complete": True, "caveats": ""}, f)

print("Done.")
