import xarray as xr
import numpy as np
import pandas as pd
import json
import os
import fsspec

# Setup filesystem
fs = fsspec.filesystem('onedata')
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
if not os.path.exists(local_path):
    fs.get(remote_path, local_path)

# Open dataset
ds = xr.open_dataset(local_path, engine="h5netcdf")

# Region bounds
lat_min, lat_max = 62.25, 63.45
lon_min, lon_max = 18.73, 19.93

# Time bounds
baseline_start_full = '1991-12-27'
baseline_end_full = '2003-01-05'
target_start = '2012-06-01'
target_end = '2012-08-31'

# Slice the dataset for the region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Baseline data
sst_baseline = ds_region.analysed_sst.sel(time=slice(baseline_start_full, baseline_end_full)).astype('float64').values
time_baseline = pd.to_datetime(ds_region.time.sel(time=slice(baseline_start_full, baseline_end_full)).values)

# Target data
sst_target = ds_region.analysed_sst.sel(time=slice(target_start, target_end)).astype('float64').values
time_target = pd.to_datetime(ds_region.time.sel(time=slice(target_start, target_end)).values)

lats = ds_region.latitude.values
lons = ds_region.longitude.values

# 1. Sea cells: SST is finite on every day of the target period
mask_sea = np.all(np.isfinite(sst_target), axis=0)

# 2. Threshold and climatology
def get_doy(dt):
    return dt.dayofyear

baseline_dates_core = time_baseline[(time_baseline >= '1992-01-01') & (time_baseline <= '2002-12-31')]
core_doy = np.array([get_doy(t) for t in baseline_dates_core])

thresholds = np.full((366, lats.size, lons.size), np.nan, dtype='float64')
climatologies = np.full((366, lats.size, lons.size), np.nan, dtype='float64')

# We'll use a dictionary to store the pool indices for each doy to speed up
for d in range(1, 367):
    if d == 60:
        continue
    
    target_dates = baseline_dates_core[core_doy == d]
    if len(target_dates) == 0:
        continue
        
    mask_pool = np.zeros(len(time_baseline), dtype=bool)
    for td in target_dates:
        diff = (time_baseline - td).days
        mask_pool |= (diff >= -5) & (diff <= 5)
    
    pool = sst_baseline[mask_pool]
    
    # Using nanquantile and nanmean; suppress warnings for all-NaN slices (land cells)
    with np.errstate(all_nan= 'ignore'):
        thresholds[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
        climatologies[d-1] = np.nanmean(pool, axis=0)

# Day 60: mean of 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

def smooth_366(arr):
    smoothed = np.zeros_like(arr)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        with np.errstate(all_nan='ignore'):
            smoothed[d] = np.nanmean(arr[indices], axis=0)
    return smoothed

thresholds_smoothed = smooth_366(thresholds)
climatologies_smoothed = smooth_366(climatologies)

# 3. Per-cell MHWs
target_doy = np.array([get_doy(t) for t in time_target])
target_thresholds = thresholds_smoothed[target_doy - 1]

hot_days = (sst_target >= target_thresholds)
hot_days = np.where(mask_sea, hot_days, False)

mhw_mask = np.zeros(hot_days.shape, dtype=np.uint8)

for i in range(lats.size):
    for j in range(lons.size):
        if not mask_sea[i, j]:
            continue
        
        cell_hot = hot_days[:, i, j]
        n_days = len(cell_hot)
        mhw_cell = np.zeros(n_days, dtype=bool)
        
        runs = []
        start = None
        for t in range(n_days):
            if cell_hot[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    runs.append((start, t - 1))
                    start = None
        if start is not None:
            runs.append((start, n_days - 1))
            
        mhw_runs = [r for r in runs if (r[1] - r[0] + 1) >= 5]
        
        if mhw_runs:
            joined = []
            curr_start, curr_end = mhw_runs[0]
            for k in range(1, len(mhw_runs)):
                next_start, next_end = mhw_runs[k]
                if next_start - curr_end - 1 <= 2:
                    curr_end = next_end
                else:
                    joined.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            joined.append((curr_start, curr_end))
            
            for s, e in joined:
                mhw_cell[s : e + 1] = True
            
        mhw_mask[:, i, j] = mhw_cell.astype(np.uint8)

# 4. Regional events
active_days = np.any(mhw_mask == 1, axis=(1, 2))

regional_events = []
start = None
for t in range(len(active_days)):
    if active_days[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            regional_events.append((time_target[start], time_target[t-1]))
            start = None
if start is not None:
    regional_events.append((time_target[start], time_target[-1]))

events_list = [{"onset": d[0].strftime('%Y-%m-%d'), "end": d[1].strftime('%Y-%m-%d')} for d in regional_events]

# Create output directory
os.makedirs('output', exist_ok=True)

# Create output NetCDF
out_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={"time": time_target, "latitude": lats, "longitude": lons}
)
out_ds.to_netcdf('output/mhw_mask.nc')

# Create report
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": time_baseline[0].strftime('%Y-%m-%d'), "end": time_baseline[-1].strftime('%Y-%m-%d')},
    "target_analysed": {"start": time_target[0].strftime('%Y-%m-%d'), "end": time_target[-1].strftime('%Y-%m-%d')},
    "events": events_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Analysis complete.")
