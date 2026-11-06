import fsspec
import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta
import os

# Ensure output directory exists
os.makedirs("output", exist_ok=True)

fs = fsspec.filesystem('onedata')
root_dir = 'icsa2027_data_20261101T090944Z/s1z'

lat_min, lat_max = 54.39, 55.59
lon_min, lon_max = 18.25, 19.45
target_start = pd.to_datetime('2021-06-01')
target_end = pd.to_datetime('2021-08-31')
baseline_start = pd.to_datetime('1992-01-01')
baseline_end = pd.to_datetime('2002-12-31')

def get_custom_doy(dt):
    # Days in months for a leap year
    days_in_months = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_months[:dt.month]) + dt.day

all_files = fs.ls(root_dir)
all_files_set = set(all_files)

def load_sst_region(start, end, lat_min, lat_max, lon_min, lon_max):
    date_range = pd.date_range(start, end)
    sst_data = []
    actual_times = []
    
    # To get the correct shape for missing files, we find the first available file
    shape = None
    for dt in date_range:
        filename = f'{root_dir}/sst_{dt.strftime("%Y%m%d")}.nc'
        if filename in all_files_set:
            with fs.open(filename, "rb") as f:
                ds = xr.open_dataset(f, engine="h5netcdf")
                region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
                data = region_ds['analysed_sst'].values.squeeze()
                if shape is None:
                    shape = data.shape
                sst_data.append(data)
                actual_times.append(dt)
        else:
            if shape is not None:
                sst_data.append(np.full(shape, np.nan))
                actual_times.append(dt)
            else:
                # We can't know the shape yet, will need to handle this
                # In this dataset, we expect files to be consistent.
                # We'll use a placeholder and fill it later or just assume it's not missing.
                actual_times.append(dt)
                sst_data.append(None)
    
    # Fix missing shapes if the first files were missing
    if any(x is None for x in sst_data):
        # Find first non-None
        first_valid = next(x for x in sst_data if x is not None)
        shape = first_valid.shape
        sst_data = [x if x is not None else np.full(shape, np.nan) for x in sst_data]
        
    return np.stack(sst_data, axis=0).astype(np.float64), actual_times

# 1. Target Period
target_sst, target_times = load_sst_region(target_start, target_end, lat_min, lat_max, lon_min, lon_max)
is_finite = np.all(np.isfinite(target_sst), axis=0)
sea_cells = is_finite

# 2. Baseline Period
baseline_load_start = baseline_start - timedelta(days=5)
baseline_load_end = baseline_end + timedelta(days=5)
baseline_sst, baseline_times = load_sst_region(baseline_load_start, baseline_load_end, lat_min, lat_max, lon_min, lon_max)

baseline_doys = np.array([get_custom_doy(t) for t in baseline_times])
thresholds = np.full((367, *sea_cells.shape), np.nan, dtype=np.float64)
climatology = np.full((367, *sea_cells.shape), np.nan, dtype=np.float64)

baseline_range_mask = (np.array(baseline_times) >= baseline_start) & (np.array(baseline_times) <= baseline_end)
baseline_indices = np.where(baseline_range_mask)[0]

doy_to_dates = {}
for idx in baseline_indices:
    d = baseline_doys[idx]
    if d not in doy_to_dates:
        doy_to_dates[d] = []
    doy_to_dates[d].append(idx)

for d in range(1, 367):
    if d == 60:
        continue
    if d not in doy_to_dates:
        continue
    
    pool_indices = set()
    for T_idx in doy_to_dates[d]:
        start_idx = max(0, T_idx - 5)
        end_idx = min(len(baseline_times) - 1, T_idx + 5)
        for idx in range(start_idx, end_idx + 1):
            pool_indices.add(idx)
    
    pool_indices = sorted(list(pool_indices))
    if not pool_indices:
        continue
    
    pool = baseline_sst[pool_indices, :, :]
    thresholds[d] = np.nanpercentile(pool, 90, axis=0, method="hazen")
    climatology[d] = np.nanmean(pool, axis=0)

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
smoothed_climatology = smooth_array(climatology)

# 3. Per-cell MHWs
target_doys = np.array([get_custom_doy(t) for t in target_times])
target_doy_indices = target_doys - 1
target_thresholds = smoothed_thresholds[target_doy_indices]
is_hot = target_sst >= target_thresholds

mhw_mask = np.zeros_like(is_hot, dtype=np.uint8)

def find_mhw_indices(hot_series):
    n = len(hot_series)
    mhw = np.zeros(n, dtype=bool)
    runs = []
    start = None
    for i in range(n):
        if hot_series[i]:
            if start is None:
                start = i
        else:
            if start is not None:
                if i - start >= 5:
                    runs.append((start, i - 1))
                start = None
    if start is not None:
        if n - start >= 5:
            runs.append((start, n - 1))
    if not runs:
        return mhw
    joined_runs = []
    curr_start, curr_end = runs[0]
    for next_start, next_end in runs[1:]:
        if next_start - curr_end - 1 <= 2:
            curr_end = next_end
        else:
            joined_runs.append((curr_start, curr_end))
            curr_start, curr_end = next_start, next_end
    joined_runs.append((curr_start, curr_end))
    for s, e in joined_runs:
        mhw[s : e + 1] = True
    return mhw

# Only process sea cells
for r in range(sea_cells.shape[0]):
    for c in range(sea_cells.shape[1]):
        if sea_cells[r, c]:
            mhw_mask[:, r, c] = find_mhw_indices(is_hot[:, r, c])

# 4. Regional events
is_active = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
start = None
for i in range(len(is_active)):
    if is_active[i]:
        if start is None:
            start = i
    else:
        if start is not None:
            regional_events.append((target_times[start], target_times[i-1]))
            start = None
if start is not None:
    regional_events.append((target_times[start], target_times[-1]))

# Coordinate extraction for the mask file
with fs.open(f'{root_dir}/sst_19820101.nc', "rb") as f:
    ds_sample = xr.open_dataset(f, engine="h5netcdf")
    lats_full = ds_sample.latitude.values
    lons_full = ds_sample.longitude.values
    lats_region = lats_full[(lats_full >= lat_min) & (lats_full <= lat_max)]
    lons_region = lons_full[(lons_full >= lon_min) & (lons_full <= lon_max)]

# Save NetCDF
ds_out = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": target_times,
        "latitude": lats_region,
        "longitude": lons_region,
    },
)
ds_out.to_netcdf("output/mhw_mask.nc")

# Save JSON
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {
        "start": baseline_load_start.strftime("%Y-%m-%d"), 
        "end": baseline_load_end.strftime("%Y-%m-%d")
    },
    "target_analysed": {
        "start": target_start.strftime("%Y-%m-%d"), 
        "end": target_end.strftime("%Y-%m-%d")
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

print("Finished successfully")
