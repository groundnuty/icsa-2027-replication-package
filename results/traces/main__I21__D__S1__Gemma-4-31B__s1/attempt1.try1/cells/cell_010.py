import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import os
import json
from datetime import timedelta

# Configuration
lat_min, lat_max = 57.33, 58.53
lon_min, lon_max = 9.03, 10.23
target_start = "2021-06-01"
target_end = "2021-08-31"
baseline_start_year = 1992
baseline_end_year = 2002

def get_doy(dt):
    """Custom day of year mapping as per instructions."""
    # dt is expected to be a pandas Timestamp or datetime object
    return dt.timetuple().tm_yday

# Setup filesystem and dataset
fs = fsspec.filesystem('onedata')
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
if not os.path.exists(local_path):
    fs.get(remote_path, local_path)

ds = xr.open_dataset(local_path, engine="h5netcdf")

# Slice region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Define target period
t_start = pd.to_datetime(target_start)
t_end = pd.to_datetime(target_end)
target_days_xr = ds_region.time.sel(time=slice(t_start, t_end))
target_sst_xr = ds_region.analysed_sst.sel(time=slice(t_start, t_end))

target_days = pd.DatetimeIndex(target_days_xr.values)
target_sst = target_sst_xr.values # (time, lat, lon)

# 1. Sea cells: finite SST on every day of the target period
finite_mask = np.all(np.isfinite(target_sst), axis=0)
sea_cells_mask = finite_mask

# 2. Threshold and Climatology
baseline_dates = pd.date_range(start=f"{baseline_start_year}-01-01", end=f"{baseline_end_year}-12-31")

# Window reach: 5 days beyond baseline
data_start = pd.to_datetime(f"{baseline_start_year-1}-12-27")
data_end = pd.to_datetime(f"{baseline_end_year+1}-01-05")
ds_baseline = ds_region.sel(time=slice(data_start, data_end))
sst_baseline = ds_baseline.analysed_sst.values
time_baseline = pd.DatetimeIndex(ds_baseline.time.values)

n_lat = len(ds_region.latitude)
n_lon = len(ds_region.longitude)
thresholds = np.full((n_lat, n_lon, 366), np.nan, dtype=np.float64)
climatologies = np.full((n_lat, n_lon, 366), np.nan, dtype=np.float64)

# Optimize pool finding
# Map each date in time_baseline to its index
date_to_idx = {date: i for i, date in enumerate(time_baseline)}

for d in range(1, 367):
    if d == 60:
        continue
    
    pool_indices = []
    for b_date in baseline_dates:
        if get_doy(b_date) == d:
            # Window [B-5, B+5]
            for offset in range(-5, 6):
                win_date = b_date + timedelta(days=offset)
                if win_date in date_to_idx:
                    pool_indices.append(date_to_idx[win_date])
    
    if not pool_indices:
        continue
    
    pool_indices = np.unique(pool_indices)
    pool_data = sst_baseline[pool_indices, :, :] # (time_pool, lat, lon)
    
    thresholds[:, :, d-1] = np.nanpercentile(pool_data, 90, axis=0, method='hazen')
    climatologies[:, :, d-1] = np.nanmean(pool_data, axis=0)

# Handle day 60
thresholds[:, :, 59] = (thresholds[:, :, 58] + thresholds[:, :, 60]) / 2
climatologies[:, :, 59] = (climatologies[:, :, 58] + climatologies[:, :, 60]) / 2

# Smoothing: 31-day centered moving mean
def smooth_31(arr):
    res = np.full_like(arr, np.nan, dtype=np.float64)
    for d in range(366):
        idx = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[:, :, idx]
        res[:, :, d] = np.nanmean(window, axis=2)
    return res

thresholds_smooth = smooth_31(thresholds)

# 3. Per-cell MHWs
target_doy = np.array([get_doy(t) for t in target_days])
thresh_reordered = np.moveaxis(thresholds_smooth, -1, 0) # (366, lat, lon)
hot_days = target_sst >= thresh_reordered[target_doy - 1, :, :]

def detect_mhw_cells_opt(hot_mask):
    time_len, n_lat, n_lon = hot_mask.shape
    flat_hot = hot_mask.reshape(time_len, -1)
    flat_mhw = np.zeros((time_len, flat_hot.shape[1]), dtype=np.uint8)
    
    for c in range(flat_hot.shape[1]):
        cell_hot = flat_hot[:, c]
        temp_mhw = np.zeros(time_len, dtype=bool)
        
        # Find runs of >= 5
        current_run = []
        for t in range(time_len):
            if cell_hot[t]:
                current_run.append(t)
            else:
                if len(current_run) >= 5:
                    temp_mhw[current_run] = True
                current_run = []
        if len(current_run) >= 5:
            temp_mhw[current_run] = True
            
        # Join gaps of 1 or 2 non-hot days
        while True:
            prev_mhw = temp_mhw.copy()
            for t in range(1, time_len - 1):
                if not temp_mhw[t] and temp_mhw[t-1] and temp_mhw[t+1]:
                    temp_mhw[t] = True
            for t in range(1, time_len - 2):
                if not temp_mhw[t] and not temp_mhw[t+1] and temp_mhw[t-1] and temp_mhw[t+2]:
                    temp_mhw[t] = True
                    temp_mhw[t+1] = True
            if np.array_equal(prev_mhw, temp_mhw):
                break
        
        flat_mhw[:, c] = temp_mhw
        
    return flat_mhw.reshape(time_len, n_lat, n_lon)

mhw_mask = detect_mhw_cells_opt(hot_days)
mhw_mask = mhw_mask * sea_cells_mask[np.newaxis, :, :]

# 4. Regional events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
in_event = False
start_day = None
for t in range(len(active_days)):
    if active_days[t]:
        if not in_event:
            in_event = True
            start_day = t
    else:
        if in_event:
            in_event = False
            regional_events.append({"onset": target_days[start_day].strftime('%Y-%m-%d'), 
                                    "end": target_days[t-1].strftime('%Y-%m-%d')})
if in_event:
    regional_events.append({"onset": target_days[start_day].strftime('%Y-%m-%d'), 
                            "end": target_days[-1].strftime('%Y-%m-%d')})

# Results
os.makedirs('output', exist_ok=True)
mhw_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask.astype(np.uint8))},
    coords={"time": target_days_xr, "latitude": ds_region.latitude, "longitude": ds_region.longitude}
)
mhw_ds.to_netcdf('output/mhw_mask.nc')

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {
        "start": time_baseline[0].strftime('%Y-%m-%d'),
        "end": time_baseline[-1].strftime('%Y-%m-%d')
    },
    "target_analysed": {
        "start": target_days[0].strftime('%Y-%m-%d'),
        "end": target_days[-1].strftime('%Y-%m-%d')
    },
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Analysis complete.")
