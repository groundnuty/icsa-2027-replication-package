import xarray as xr
import numpy as np
import pandas as pd
import os
import json
from datetime import datetime, timedelta

# Constants
LAT_MIN, LAT_MAX = 63.31, 64.51
LON_MIN, LON_MAX = 21.31, 22.51
TARGET_START = '2009-06-01'
TARGET_END = '2009-08-31'
BASELINE_START = '1992-01-01'
BASELINE_END = '2002-12-31'
DIR_PATH = '/data/icsa2027_data_20261101T090944Z/s1z'

def get_files_for_range(start_date, end_date):
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    all_files = os.listdir(DIR_PATH)
    sst_files = [f for f in all_files if f.startswith('sst_') and f.endswith('.nc')]
    matching_files = []
    for f in sst_files:
        date_str = f[4:12]
        f_date = pd.to_datetime(date_str, format='%Y%m%d')
        if start <= f_date <= end:
            matching_files.append(f)
    matching_files.sort()
    return matching_files

def load_region_sst(files):
    datasets = []
    for f in files:
        ds = xr.open_dataset(os.path.join(DIR_PATH, f), engine='h5netcdf')
        ds_region = ds.sel(latitude=slice(LAT_MIN, LAT_MAX), longitude=slice(LON_MIN, LON_MAX))
        datasets.append(ds_region)
    return xr.concat(datasets, dim='time')

# 1. Load Target Data and Find Sea Cells
target_files = get_files_for_range(TARGET_START, TARGET_END)
ds_target = load_region_sst(target_files)
sst_target = ds_target['analysed_sst'].astype('float64')
is_finite = np.all(np.isfinite(sst_target.values), axis=0)
sea_cells_mask = is_finite

# 2. Threshold and Climatology
b_start_dt = pd.to_datetime(BASELINE_START)
b_end_dt = pd.to_datetime(BASELINE_END)
ext_start = b_start_dt - pd.Timedelta(days=5)
ext_end = b_end_dt + pd.Timedelta(days=5)

baseline_files = get_files_for_range(ext_start.strftime('%Y-%m-%d'), ext_end.strftime('%Y-%m-%d'))
ds_baseline = load_region_sst(baseline_files)
sst_baseline = ds_baseline['analysed_sst'].astype('float64')
time_baseline = sst_baseline.time.values

date_to_idx = {pd.to_datetime(t): i for i, t in enumerate(time_baseline)}
baseline_dates = pd.date_range(b_start_dt, b_end_dt)

thresholds_raw = np.full((367, sst_baseline.latitude.size, sst_baseline.longitude.size), np.nan)
climatology_raw = np.full((367, sst_baseline.latitude.size, sst_baseline.longitude.size), np.nan)

used_dates = set()
for d in range(1, 367):
    if d == 60:
        continue
    b_dates = [b for b in baseline_dates if b.day_of_year == d]
    pool_dates = set()
    for b in b_dates:
        for offset in range(-5, 6):
            pool_dates.add(b + pd.Timedelta(days=offset))
    
    indices = [date_to_idx[t] for t in pool_dates if t in date_to_idx]
    if indices:
        pool_sst = sst_baseline.values[indices]
        thresholds_raw[d] = np.nanquantile(pool_sst, 0.9, axis=0, method='hazen')
        climatology_raw[d] = np.nanmean(pool_sst, axis=0)
        used_dates.update(pool_dates)

thresholds_raw[60] = (thresholds_raw[59] + thresholds_raw[61]) / 2
climatology_raw[60] = (climatology_raw[59] + climatology_raw[61]) / 2

def smooth_366(arr):
    data = arr[1:] # (366, lat, lon)
    smoothed = np.full_like(data, np.nan)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        smoothed[d] = np.nanmean(data[indices], axis=0)
    return smoothed

thresholds_smooth = smooth_366(thresholds_raw)
climatology_smooth = smooth_366(climatology_raw)

# 3. Per-cell MHWs
target_dates = pd.to_datetime(sst_target.time.values)
mhw_mask = np.zeros(sst_target.shape, dtype=np.uint8)
lats = sst_target.latitude.values
lons = sst_target.longitude.values

for i in range(len(lats)):
    for j in range(len(lons)):
        if not sea_cells_mask[i, j]:
            continue
        cell_sst = sst_target.values[:, i, j]
        cell_thresholds = np.array([thresholds_smooth[t.day_of_year - 1, i, j] for t in target_dates])
        hot = cell_sst >= cell_thresholds
        n_days = len(hot)
        in_mhw = np.zeros(n_days, dtype=bool)
        runs = []
        start = None
        for d in range(n_days):
            if hot[d]:
                if start is None: start = d
            else:
                if start is not None:
                    if d - start >= 5: runs.append((start, d - 1))
                    start = None
        if start is not None and n_days - start >= 5:
            runs.append((start, n_days - 1))
        if runs:
            merged = []
            curr_start, curr_end = runs[0]
            for next_start, next_end in runs[1:]:
                if next_start - curr_end - 1 <= 2:
                    curr_end = next_end
                else:
                    merged.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            merged.append((curr_start, curr_end))
            for s, e in merged:
                in_mhw[s : e + 1] = True
        mhw_mask[:, i, j] = in_mhw.astype(np.uint8)

# 4. Regional Events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
start = None
for d in range(len(active_days)):
    if active_days[d]:
        if start is None: start = d
    else:
        if start is not None:
            regional_events.append((target_dates[start], target_dates[d-1]))
            start = None
if start is not None:
    regional_events.append((target_dates[start], target_dates[-1]))

onset_end_events = [{"onset": e[0].strftime('%Y-%m-%d'), "end": e[1].strftime('%Y-%m-%d')} for e in regional_events]

os.makedirs('output', exist_ok=True)
ds_out = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={"time": target_dates, "latitude": lats, "longitude": lons}
)
ds_out.to_netcdf('output/mhw_mask.nc')

actual_b_start = min(used_dates).strftime('%Y-%m-%d') if used_dates else None
actual_b_end = max(used_dates).strftime('%Y-%m-%d') if used_dates else None

report = {
    "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
    "baseline_analysed": {"start": actual_b_start, "end": actual_b_end},
    "target_analysed": {"start": TARGET_START, "end": TARGET_END},
    "events": onset_end_events,
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Done")
