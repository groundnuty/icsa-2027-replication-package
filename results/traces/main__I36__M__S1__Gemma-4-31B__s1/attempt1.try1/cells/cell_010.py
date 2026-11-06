import os
import glob
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
    doy = sum(month_days[:dt.month - 1]) + dt.day
    if dt.month > 2:
        doy += 1
    return doy

all_files = sorted(glob.glob(os.path.join(DATA_DIR, "sst_*.nc")))
win_start_limit = BASELINE_START - timedelta(days=5)
win_end_limit = BASELINE_END + timedelta(days=5)

baseline_files_info = []
for f in all_files:
    fname = os.path.basename(f)
    if not (fname.startswith("sst_") and fname.endswith(".nc")): continue
    try:
        dt = datetime.strptime(fname[4:-3], "%Y%m%d")
        if win_start_limit <= dt <= win_end_limit:
            baseline_files_info.append((dt, f))
    except ValueError: pass
baseline_files_info.sort()

target_files_info = []
for f in all_files:
    fname = os.path.basename(f)
    if not (fname.startswith("sst_") and fname.endswith(".nc")): continue
    try:
        dt = datetime.strptime(fname[4:-3], "%Y%m%d")
        if TARGET_START <= dt <= TARGET_END:
            target_files_info.append((dt, f))
    except ValueError: pass
target_files_info.sort()

def load_sst_region(files_info):
    if not files_info: return None, None, None, None
    sst_list, dates, lats, lons = [], [], None, None
    for dt, f in files_info:
        with xr.open_dataset(f, engine="h5netcdf") as ds:
            region_ds = ds.sel(latitude=slice(LAT_MIN, LAT_MAX), longitude=slice(LON_MIN, LON_MAX))
            sst = region_ds.analysed_sst.values.astype(np.float64)
            sst_list.append(sst)
            dates.append(dt)
            if lats is None:
                lats, lons = region_ds.latitude.values, region_ds.longitude.values
    return np.array(sst_list), np.array(dates), lats, lons

print("Loading data...")
baseline_sst, baseline_dates, lats, lons = load_sst_region(baseline_files_info)
target_sst, target_dates, _, _ = load_sst_region(target_files_info)

if target_sst is None:
    os.makedirs("output", exist_ok=True)
    xr.Dataset({"mhw": (("time", "latitude", "longitude"), np.array([], dtype=np.uint8))}, 
               coords={"time": np.array([], dtype='datetime64[ns]'), "latitude": np.array([]), "longitude": np.array([])}).to_netcdf("output/mhw_mask.nc")
    with open("output/report.json", "w") as f:
        json.dump({"region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX}, "baseline_analysed": None, "target_analysed": None, "events": [], "complete": True, "caveats": "No target data"}, f)
    print("Done (no target data).")
    exit()

n_lat, n_lon = lats.size, lons.size
is_sea = np.all(np.isfinite(target_sst), axis=0)

thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60: continue
    baseline_doy_d_indices = [i for i, (dt, _) in enumerate(baseline_files_info) if BASELINE_START <= dt <= BASELINE_END and get_day_of_year(dt) == d]
    pool_indices = set()
    for idx in baseline_doy_d_indices:
        base_dt = baseline_dates[idx]
        s_pos = np.searchsorted(baseline_dates, base_dt - timedelta(days=5))
        e_pos = np.searchsorted(baseline_dates, base_dt + timedelta(days=5), side='right')
        pool_indices.update(range(s_pos, e_pos))
    if pool_indices:
        pool_data = baseline_sst[sorted(list(pool_indices)), :, :]
        thresholds[d-1] = np.nanpercentile(pool_data, 90, axis=0, method="hazen")
        climatology[d-1] = np.nanmean(pool_data, axis=0)

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

n_target_days = target_sst.shape[0]
mhw_mask = np.zeros((n_target_days, n_lat, n_lon), dtype=np.uint8)

# Target thresholds array for each day: (n_target_days, n_lat, n_lon)
target_doy_indices = np.array([get_day_of_year(dt) - 1 for dt in target_dates])
target_thresholds = thresholds[target_doy_indices, :, :]
hot_days = (target_sst >= target_thresholds)

for r in range(n_lat):
    for c in range(n_lon):
        if not bool(is_sea[r, c]): continue
        
        cell_hot = hot_days[:, r, c]
        is_mhw = np.zeros(n_target_days, dtype=bool)
        
        # Runs of hot days
        runs = []
        start = None
        for i in range(n_target_days):
            if cell_hot[i]:
                if start is None: start = i
            else:
                if start is not None:
                    runs.append((start, i-1))
                    start = None
        if start is not None: runs.append((start, n_target_days-1))
        
        # Filter >= 5 days
        valid_runs = [run for run in runs if (run[1] - run[0] + 1) >= 5]
        if valid_runs:
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
                is_mhw[s:e+1] = True
        mhw_mask[:, r, c] = is_mhw.astype(np.uint8)

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

os.makedirs("output", exist_ok=True)
xr.Dataset({"mhw": (("time", "latitude", "longitude"), mhw_mask)}, 
           coords={"time": target_dates, "latitude": lats, "longitude": lons}).to_netcdf("output/mhw_mask.nc")

all_used_baseline_indices = set()
for d in range(1, 367):
    if d == 60: continue
    baseline_doy_d_indices = [i for i, (dt, _) in enumerate(baseline_files_info) if BASELINE_START <= dt <= BASELINE_END and get_day_of_year(dt) == d]
    for idx in baseline_doy_d_indices:
        base_dt = baseline_dates[idx]
        s_pos = np.searchsorted(baseline_dates, base_dt - timedelta(days=5))
        e_pos = np.searchsorted(baseline_dates, base_dt + timedelta(days=5), side='right')
        all_used_baseline_indices.update(range(s_pos, e_pos))

baseline_analysed = None
if all_used_baseline_indices:
    indices = sorted(list(all_used_baseline_indices))
    baseline_analysed = {"start": baseline_dates[indices[0]].strftime("%Y-%m-%d"), "end": baseline_dates[indices[-1]].strftime("%Y-%m-%d")}

with open("output/report.json", "w") as f:
    json.dump({"region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX}, 
               "baseline_analysed": baseline_analysed,
               "target_analysed": {"start": target_dates[0].strftime("%Y-%m-%d"), "end": target_dates[-1].strftime("%Y-%m-%d")},
               "events": events, "complete": True, "caveats": ""}, f)

print("Done.")
