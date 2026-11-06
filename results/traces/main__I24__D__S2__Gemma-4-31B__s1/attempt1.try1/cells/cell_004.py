import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
import os
from datetime import datetime, timedelta

# Setup filesystem
fs = fsspec.filesystem('onedata')
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
if not os.path.exists(local_path):
    fs.get(remote_path, local_path)

ds = xr.open_dataset(local_path, engine="h5netcdf")

# Region
lat_min, lat_max = 57.57, 58.77
lon_min, lon_max = 10.25, 11.45

# Target period
target_start_str = '2004-06-01'
target_end_str = '2004-08-31'
target_start = pd.to_datetime(target_start_str)
target_end = pd.to_datetime(target_end_str)

# Baseline range
baseline_start_date = pd.to_datetime('1992-01-01')
baseline_end_date = pd.to_datetime('2002-12-31')
ext_baseline_start = pd.to_datetime('1991-12-27')
ext_baseline_end = pd.to_datetime('2003-01-05')

# Slice region
ds_reg = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Slice time
ds_baseline = ds_reg.sel(time=slice(ext_baseline_start, ext_baseline_end))
ds_target = ds_reg.sel(time=slice(target_start, target_end))

def get_doy(dt):
    month = dt.month
    day = dt.day
    month_offsets = [0, 0, 31, 60, 91, 121, 151, 181, 212, 243, 273, 304, 334]
    return month_offsets[month] + day

# Precompute DOY for all dates in the extended baseline
baseline_times = ds_baseline.time.values
baseline_doy = np.array([get_doy(pd.to_datetime(t)) for t in baseline_times])

# Thresholds and Climatology
n_lat = ds_reg.latitude.size
n_lon = ds_reg.longitude.size
thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

sst_vals = ds_baseline.analysed_sst.values.astype(np.float64)
baseline_period_mask = (baseline_times >= np.datetime64('1992-01-01')) & (baseline_times <= np.datetime64('2002-12-31'))
baseline_period_indices = np.where(baseline_period_mask)[0]

for d in range(1, 367):
    if d == 60:
        continue
    
    d_indices = [idx for idx in baseline_period_indices if baseline_doy[idx] == d]
    if not d_indices:
        continue
        
    pool_indices = set()
    for idx in d_indices:
        pool_indices.update(range(max(0, idx-5), min(len(baseline_times), idx+6)))
    
    pool_indices = sorted(list(pool_indices))
    if not pool_indices:
        continue
        
    pool = sst_vals[pool_indices, :, :]
    thresholds[d-1] = np.nanpercentile(pool, 90, axis=0, method="hazen")
    climatology[d-1] = np.nanmean(pool, axis=0)

thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

def smooth_366(arr):
    smoothed = np.full_like(arr, np.nan, dtype=np.float64)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices, :, :]
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

thresholds_smooth = smooth_366(thresholds)
climatology_smooth = smooth_366(climatology)

target_sst = ds_target.analysed_sst.values.astype(np.float64)
target_times = ds_target.time.values
target_doy = np.array([get_doy(pd.to_datetime(t)) for t in target_times])

is_hot = target_sst >= thresholds_smooth[target_doy - 1, :, :]
sea_cells_mask = np.all(np.isfinite(target_sst), axis=0)

n_days = target_sst.shape[0]
mhw_mask = np.zeros((n_days, n_lat, n_lon), dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells_mask[i, j]:
            continue
            
        hot = is_hot[:, i, j]
        temp_mhw = np.zeros(n_days, dtype=bool)
        
        count = 0
        start_idx = 0
        for t in range(n_days):
            if hot[t]:
                if count == 0:
                    start_idx = t
                count += 1
            else:
                if count >= 5:
                    temp_mhw[start_idx : start_idx + count] = True
                count = 0
        if count >= 5:
            temp_mhw[start_idx : start_idx + count] = True
            
        changed = True
        while changed:
            changed = False
            for t in range(1, n_days - 1):
                if not temp_mhw[t]:
                    if temp_mhw[t-1] and temp_mhw[t+1]:
                        temp_mhw[t] = True
                        changed = True
                    elif t < n_days - 2 and not temp_mhw[t+1] and temp_mhw[t-1] and temp_mhw[t+2]:
                        temp_mhw[t] = True
                        temp_mhw[t+1] = True
                        changed = True
        
        mhw_mask[:, i, j] = temp_mhw.astype(np.uint8)

active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
count = 0
start_idx = 0
for t in range(n_days):
    if active_days[t]:
        if count == 0:
            start_idx = t
        count += 1
    else:
        if count > 0:
            regional_events.append({
                "onset": target_times[start_idx].astype('datetime64[D]').astype(str),
                "end": target_times[t-1].astype('datetime64[D]').astype(str)
            })
        count = 0
if count > 0:
    regional_events.append({
        "onset": target_times[start_idx].astype('datetime64[D]').astype(str),
        "end": target_times[n_days-1].astype('datetime64[D]').astype(str)
    })

mhw_da = xr.DataArray(
    mhw_mask,
    coords={"time": target_times, "latitude": ds_reg.latitude, "longitude": ds_reg.longitude},
    dims=("time", "latitude", "longitude"),
    name="mhw"
).astype(np.uint8)

mhw_ds = mhw_da.to_dataset()
os.makedirs('output', exist_ok=True)
mhw_ds.to_netcdf('output/mhw_mask.nc')

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {"start": target_start_str, "end": target_end_str},
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Done")
