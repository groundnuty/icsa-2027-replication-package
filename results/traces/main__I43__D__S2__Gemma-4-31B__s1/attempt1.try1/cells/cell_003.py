import xarray as xr
import numpy as np
import pandas as pd
import datetime
import json
import os

# Constants
REGION = {"lat_min": 62.25, "lat_max": 63.45, "lon_min": 18.73, "lon_max": 19.93}
TARGET_START = "2017-06-01"
TARGET_END = "2017-08-31"
BASELINE_START = "1992-01-01"
BASELINE_END = "2002-12-31"
REMOTE_PATH = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
LOCAL_PATH = "/work/sst_s2.nc"

def get_doy_fixed(dt):
    """Map date to DOY 1-366 based on month and day."""
    yday = (dt - datetime.date(dt.year, 1, 1)).days + 1
    is_leap = (dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0))
    if not is_leap and yday > 59:
        return yday + 1
    return yday

# Download and load
import fsspec
fs = fsspec.filesystem('onedata')
if not os.path.exists(LOCAL_PATH):
    fs.get(REMOTE_PATH, LOCAL_PATH)

ds = xr.open_dataset(LOCAL_PATH, engine="h5netcdf")

# Slice to region
ds_reg = ds.sel(
    latitude=slice(REGION["lat_min"], REGION["lat_max"]),
    longitude=slice(REGION["lon_min"], REGION["lon_max"])
)

# Target period
target_start_dt = pd.to_datetime(TARGET_START)
target_end_dt = pd.to_datetime(TARGET_END)
ds_target = ds_reg.sel(time=slice(target_start_dt, target_end_dt))

# Identify sea cells: SST finite on every day of target period
sst_target = ds_target['analysed_sst'].astype(np.float64)
# Use xarray's all() method or np.all with axis
sea_mask = sst_target.isfinite().all(dim='time').values

# Baseline period and window extensions
baseline_start_dt = pd.to_datetime(BASELINE_START).date()
baseline_end_dt = pd.to_datetime(BASELINE_END).date()
pool_start_dt = pd.to_datetime(baseline_start_dt - datetime.timedelta(days=5))
pool_end_dt = pd.to_datetime(baseline_end_dt + datetime.timedelta(days=5))
ds_pool = ds_reg.sel(time=slice(pool_start_dt, pool_end_dt))
sst_pool = ds_pool['analysed_sst'].astype(np.float64)

# Map baseline dates to DOY
baseline_dates = pd.date_range(baseline_start_dt, baseline_end_dt)
doy_baseline_dates = {}
for dt in baseline_dates:
    d = get_doy_fixed(dt.date())
    if d not in doy_baseline_dates:
        doy_baseline_dates[d] = []
    doy_baseline_dates[d].append(pd.to_datetime(dt))

# Find dataset dates for each DOY pool
dataset_dates = pd.to_datetime(ds_pool.time.values)
doy_pools_indices = {} 
for d in range(1, 367):
    if d == 60:
        continue
    b_dates = doy_baseline_dates.get(d, [])
    pool_indices = []
    for b_date in b_dates:
        mask = (dataset_dates >= b_date - pd.Timedelta(days=5)) & \
               (dataset_dates <= b_date + pd.Timedelta(days=5))
        pool_indices.extend(np.where(mask)[0])
    doy_pools_indices[d] = np.unique(pool_indices)

# Thresholds and Climatology
lats = ds_reg.latitude.values
lons = ds_reg.longitude.values
n_lat = len(lats)
n_lon = len(lons)

thresholds = np.full((367, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((367, n_lat, n_lon), np.nan, dtype=np.float64)

sst_pool_vals = sst_pool.values

for d in range(1, 367):
    if d == 60:
        continue
    indices = doy_pools_indices[d]
    if len(indices) == 0:
        continue
    pool_data = sst_pool_vals[indices]
    reshaped_pool = pool_data.reshape(len(indices), -1)
    
    q90 = np.nanquantile(reshaped_pool, 0.9, axis=0, method='hazen')
    mean_val = np.nanmean(reshaped_pool, axis=0)
    
    thresholds[d] = q90.reshape(n_lat, n_lon)
    climatology[d] = mean_val.reshape(n_lat, n_lon)

# Handle day 60
thresholds[60] = (thresholds[59] + thresholds[61]) / 2
climatology[60] = (climatology[59] + climatology[61]) / 2

# Smoothing: 31-day centred moving mean
def smooth_array(arr):
    data = arr[1:] # (366, n_lat, n_lon)
    smoothed = np.full_like(data, np.nan)
    for d in range(366):
        window_indices = [(d - 15 + i) % 366 for i in range(31)]
        window_data = data[window_indices]
        smoothed[d] = np.nanmean(window_data, axis=0)
    return smoothed

thresholds_smooth = smooth_array(thresholds)
climatology_smooth = smooth_array(climatology)

# Detect MHWs in the target period
sst_target_vals = sst_target.values
target_dates = pd.to_datetime(ds_target.time.values)
n_target_days = len(target_dates)
target_doys_idx = [get_doy_fixed(dt.date()) - 1 for dt in target_dates]

mhw_mask = np.zeros((n_target_days, n_lat, n_lon), dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_mask[i, j]:
            continue
        
        cell_sst = sst_target_vals[:, i, j]
        cell_thresholds = np.array([thresholds_smooth[d][i, j] for d in target_doys_idx])
        
        hot = cell_sst >= cell_thresholds
        is_mhw = np.zeros(n_target_days, dtype=bool)
        
        runs = []
        start = None
        for t in range(n_target_days):
            if hot[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    if t - start >= 5:
                        runs.append((start, t - 1))
                    start = None
        if start is not None:
            if n_target_days - start >= 5:
                runs.append((start, n_target_days - 1))
        
        if not runs:
            continue
            
        merged = []
        curr_start, curr_end = runs[0]
        for next_start, next_end in runs[1:]:
            if next_start - curr_end <= 3:
                curr_end = next_end
            else:
                merged.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged.append((curr_start, curr_end))
        
        for start, end in merged:
            is_mhw[start : end + 1] = True
        
        mhw_mask[:, i, j] = is_mhw.astype(np.uint8)

# Regional Events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
start = None
for t in range(n_target_days):
    if active_days[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            regional_events.append((target_dates[start], target_dates[t-1]))
            start = None
if start is not None:
    regional_events.append((target_dates[start], target_dates[n_target_days-1]))

# Save results
mask_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": ds_target.time,
        "latitude": ds_reg.latitude,
        "longitude": ds_reg.longitude,
    }
)
os.makedirs("output", exist_ok=True)
mask_ds.to_netcdf("output/mhw_mask.nc")

report = {
    "region": REGION,
    "baseline_analysed": {"start": BASELINE_START, "end": BASELINE_END},
    "target_analysed": {"start": TARGET_START, "end": TARGET_END},
    "events": [
        {"onset": e[0].strftime("%Y-%m-%d"), "end": e[1].strftime("%Y-%m-%d")}
        for e in regional_events
    ],
    "complete": True,
    "caveats": ""
}

with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Done")
