import xarray as xr
import numpy as np
import pandas as pd
import json
import os
from datetime import datetime, timedelta

def get_doy(dt):
    month = dt.month
    day = dt.day
    days_before = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    doy = days_before[month-1] + day
    if month > 2:
        doy += 1
    return doy

# Parameters
lat_min, lat_max = 54.45, 55.65
lon_min, lon_max = 16.05, 17.25
target_start_str = '2021-06-01'
target_end_str = '2021-08-31'
baseline_start_str = '1992-01-01'
baseline_end_str = '2002-12-31'

ds_path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(ds_path, engine="h5netcdf")

# Region subset
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

t_start = pd.to_datetime(target_start_str)
t_end = pd.to_datetime(target_end_str)
b_start = pd.to_datetime(baseline_start_str)
b_end = pd.to_datetime(baseline_end_str)

b_pool_start = b_start - pd.Timedelta(days=5)
b_pool_end = b_end + pd.Timedelta(days=5)

# Target and Baseline Data
ds_target_slice = ds_region.sel(time=slice(t_start, t_end))
sst_target = ds_target_slice.analysed_sst.astype(np.float64).values
time_target_vals = ds_target_slice.time.values

ds_baseline_slice = ds_region.sel(time=slice(b_pool_start, b_pool_end))
sst_baseline = ds_baseline_slice.analysed_sst.astype(np.float64).values
time_baseline_vals = ds_baseline_slice.time.values

lat_vals = ds_region.latitude.values
lon_vals = ds_region.longitude.values

# 1. Sea cells: SST finite on every day of the target period
sea_mask = np.all(np.isfinite(sst_target), axis=0)

# 2. Threshold and Climatology
baseline_dates = pd.to_datetime(time_baseline_vals)
baseline_period_mask = (baseline_dates >= b_start) & (baseline_dates <= b_end)
baseline_period_indices = np.where(baseline_period_mask)[0]

doy_to_baseline_indices = {d: [] for d in range(1, 367)}
for idx in baseline_period_indices:
    d = get_doy(baseline_dates[idx])
    if d != 60:
        doy_to_baseline_indices[d].append(idx)

doy_to_pool_indices = {d: [] for d in range(1, 367)}
for d in range(1, 367):
    if d == 60: continue
    pool_indices = set()
    for idx in doy_to_baseline_indices[d]:
        for win_idx in range(idx - 5, idx + 6):
            if 0 <= win_idx < len(baseline_dates):
                pool_indices.add(win_idx)
    doy_to_pool_indices[d] = list(pool_indices)

thresholds = np.full((367, len(lat_vals), len(lon_vals)), np.nan, dtype=np.float64)
climatologies = np.full((367, len(lat_vals), len(lon_vals)), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60: continue
    pool_idx = doy_to_pool_indices[d]
    if not pool_idx: continue
    
    sst_pool = sst_baseline[pool_idx, :, :]
    thresholds[d] = np.nanquantile(sst_pool, 0.9, axis=0, method='hazen')
    climatologies[d] = np.nanmean(sst_pool, axis=0)

thresholds[60] = (thresholds[59] + thresholds[61]) / 2
climatologies[60] = (climatologies[59] + climatologies[61]) / 2

def smooth_366(arr):
    # arr is (367, lat, lon)
    smoothed = np.full((367, arr.shape[1], arr.shape[2]), np.nan, dtype=np.float64)
    data = arr[1:] # (366, lat, lon)
    for d in range(366):
        window_indices = [(d + i) % 366 for i in range(-15, 16)]
        smoothed[d+1] = np.nanmean(data[window_indices], axis=0)
    return smoothed

thresholds_smooth = smooth_366(thresholds)
climatologies_smooth = smooth_366(climatologies)

# 3. Per-cell MHWs
target_doy = np.array([get_doy(pd.to_datetime(dt)) for dt in time_target_vals])
hot_mask = np.zeros(sst_target.shape, dtype=bool)
for t in range(len(target_doy)):
    d = target_doy[t]
    hot_mask[t] = sst_target[t] >= thresholds_smooth[d]

mhw_mask = np.zeros(sst_target.shape, dtype=np.uint8)
for lat_idx in range(len(lat_vals)):
    for lon_idx in range(len(lon_vals)):
        if not sea_mask[lat_idx, lon_idx]:
            continue
        
        hot_days = hot_mask[:, lat_idx, lon_idx]
        in_mhw = np.zeros(len(hot_days), dtype=bool)
        
        count = 0
        for t in range(len(hot_days)):
            if hot_days[t]:
                count += 1
            else:
                if count >= 5:
                    in_mhw[t-count : t] = True
                count = 0
        if count >= 5:
            in_mhw[len(hot_days)-count:] = True
            
        changed = True
        while changed:
            changed = False
            for t in range(1, len(hot_days) - 1):
                if not in_mhw[t]:
                    if in_mhw[t-1] and in_mhw[t+1]:
                        in_mhw[t] = True
                        changed = True
                    elif t < len(hot_days)-2 and in_mhw[t-1] and not in_mhw[t+1] and in_mhw[t+2]:
                        in_mhw[t] = True
                        in_mhw[t+1] = True
                        changed = True
        mhw_mask[:, lat_idx, lon_idx] = in_mhw.astype(np.uint8)

# 4. Regional events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
in_event = False
onset = None

for t in range(len(active_days)):
    if active_days[t] and not in_event:
        in_event = True
        onset = time_target_vals[t]
    elif not active_days[t] and in_event:
        in_event = False
        regional_events.append({
            "onset": pd.to_datetime(onset).strftime('%Y-%m-%d'), 
            "end": pd.to_datetime(time_target_vals[t-1]).strftime('%Y-%m-%d')
        })
if in_event:
    regional_events.append({
        "onset": pd.to_datetime(onset).strftime('%Y-%m-%d'), 
        "end": pd.to_datetime(time_target_vals[-1]).strftime('%Y-%m-%d')
    })

# Write Results
os.makedirs('output', exist_ok=True)
ds_out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw_mask)},
    coords={"time": time_target_vals, "lat": lat_vals, "lon": lon_vals}
)
ds_out.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": baseline_start_str, "end": baseline_end_str},
    "target_analysed": {"start": target_start_str, "end": target_end_str},
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Done.")
