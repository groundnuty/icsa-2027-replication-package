import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# Parameters
LAT_MIN, LAT_MAX = 57.83, 59.03
LON_MIN, LON_MAX = 17.41, 18.61
TARGET_START = "2008-06-01"
TARGET_END = "2008-08-31"
BASELINE_START = "1992-01-01"
BASELINE_END = "2002-12-31"

def get_doy(date):
    """Maps a date to a day of year from 1 to 366."""
    # 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61
    days_in_months = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_months[:date.month - 1]) + date.day

# Ensure output directory exists
os.makedirs("output", exist_ok=True)

# Load dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', engine="h5netcdf")

# Region slicing
lat_idx = np.where((ds.latitude.values >= LAT_MIN) & (ds.latitude.values <= LAT_MAX))[0]
lon_idx = np.where((ds.longitude.values >= LON_MIN) & (ds.longitude.values <= LON_MAX))[0]
ds_region = ds.isel(latitude=slice(lat_idx[0], lat_idx[-1]+1), longitude=slice(lon_idx[0], lon_idx[-1]+1))

# Target period slicing
target_ds = ds_region.sel(time=slice(TARGET_START, TARGET_END))
target_times = target_ds.time.values
target_sst = target_ds.analysed_sst.values.astype(np.float64)

# Sea cells: finite SST on every day of the target period
is_finite = np.all(np.isfinite(target_sst), axis=0)
sea_cells_mask = is_finite 

# Baseline Period
baseline_dates = pd.date_range(BASELINE_START, BASELINE_END)
extended_start = pd.Timestamp(BASELINE_START) - pd.Timedelta(days=5)
extended_end = pd.Timestamp(BASELINE_END) + pd.Timedelta(days=5)

# Slice the dataset for the extended range
baseline_ext_ds = ds_region.sel(time=slice(extended_start.strftime('%Y-%m-%d'), extended_end.strftime('%Y-%m-%d')))
baseline_ext_sst = baseline_ext_ds.analysed_sst.values.astype(np.float64)
baseline_ext_times = baseline_ext_ds.time.values

date_to_idx = {np.datetime64(d).astype('datetime64[ns]'): i for i, d in enumerate(baseline_ext_times)}
base_range_indices = [date_to_idx[np.datetime64(d).astype('datetime64[ns]')] for d in baseline_dates]
base_doy = np.array([get_doy(d.to_pydatetime()) for d in baseline_dates])

# Pools
thresholds = np.full((366, ds_region.latitude.size, ds_region.longitude.size), np.nan, dtype=np.float64)
climatologies = np.full((366, ds_region.latitude.size, ds_region.longitude.size), np.nan, dtype=np.float64)

# To track actual dates used in the baseline
used_dates = set()

for d in range(1, 367):
    if d == 60:
        continue
    
    matching_indices = np.where(base_doy == d)[0]
    if len(matching_indices) == 0:
        continue
        
    pool_indices = set()
    for idx in matching_indices:
        date = baseline_dates[idx]
        for offset in range(-5, 6):
            win_date = date + pd.Timedelta(days=offset)
            win_date_np = np.datetime64(win_date).astype('datetime64[ns]')
            if win_date_np in date_to_idx:
                pool_indices.add(date_to_idx[win_date_np])
                used_dates.add(win_date_np)
    
    pool_indices = list(pool_indices)
    pool_sst = baseline_ext_sst[pool_indices, :, :]
    
    thresholds[d-1] = np.nanquantile(pool_sst, 0.9, axis=0, method="hazen")
    climatologies[d-1] = np.nanmean(pool_sst, axis=0)

# Day 60
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

def smooth(arr):
    smoothed = np.zeros_like(arr)
    for d in range(366):
        indices = [(d - 15 + i) % 366 for i in range(31)]
        smoothed[d] = np.nanmean(arr[indices], axis=0)
    return smoothed

thresholds_smoothed = smooth(thresholds)

# Per-cell MHWs
target_doy = np.array([get_doy(pd.Timestamp(t).to_pydatetime()) for t in target_times])
target_doy_idx = target_doy - 1
thresholds_at_target = thresholds_smoothed[target_doy_idx]
hot_mask = target_sst >= thresholds_at_target

mhw_mask = np.zeros(hot_mask.shape, dtype=np.uint8)
lat_size, lon_size = ds_region.latitude.size, ds_region.longitude.size

for i in range(lat_size):
    for j in range(lon_size):
        if not sea_cells_mask[i, j]:
            continue
        
        cell_hot = hot_mask[:, i, j]
        cell_mhw = np.zeros(len(cell_hot), dtype=bool)
        
        runs = []
        start = None
        for t in range(len(cell_hot)):
            if cell_hot[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    if t - start >= 5:
                        runs.append((start, t - 1))
                    start = None
        if start is not None:
            if len(cell_hot) - start >= 5:
                runs.append((start, len(cell_hot) - 1))
        
        if not runs:
            continue
            
        merged_runs = []
        curr_start, curr_end = runs[0]
        for next_start, next_end in runs[1:]:
            if next_start - curr_end <= 3:
                curr_end = next_end
            else:
                merged_runs.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged_runs.append((curr_start, curr_end))
            
        for start, end in merged_runs:
            cell_mhw[start:end+1] = True
            
        mhw_mask[:, i, j] = cell_mhw.astype(np.uint8)

# Regional events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
start = None
for t in range(len(active_days)):
    if active_days[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            regional_events.append((target_times[start], target_times[t-1]))
            start = None
if start is not None:
    regional_events.append((target_times[start], target_times[-1]))

events_list = [{"onset": np.datetime64(start).astype('datetime64[D]').astype(str), 
                "end": np.datetime64(end).astype('datetime64[D]').astype(str)} 
               for start, end in regional_events]

# Baseline analysis dates
if used_dates:
    baseline_analysed_start = min(used_dates).astype('datetime64[D]').astype(str)
    baseline_analysed_end = max(used_dates).astype('datetime64[D]').astype(str)
else:
    baseline_analysed_start = baseline_analysed_end = None

# Save mhw_mask.nc
mhw_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={"time": target_times, "latitude": ds_region.latitude, "longitude": ds_region.longitude}
)
mhw_ds.to_netcdf("output/mhw_mask.nc")

# Save report.json
report = {
    "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
    "baseline_analysed": {"start": baseline_analysed_start, "end": baseline_analysed_end},
    "target_analysed": {"start": TARGET_START, "end": TARGET_END},
    "events": events_list,
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Done")
