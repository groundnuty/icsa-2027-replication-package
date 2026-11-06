import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta

def get_doy(dt):
    """Custom day of year mapping as per instructions."""
    month = dt.month
    day = dt.day
    # Days before the start of each month (non-leap)
    # Jan:0, Feb:31, Mar:59, Apr:90, May:120, Jun:151, Jul:181, Aug:212, Sep:243, Oct:273, Nov:304, Dec:334
    days_before = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    doy = days_before[month-1] + day
    if month > 2:
        doy += 1
    # If leap year and Feb 29, doy is 31 + 29 = 60. Correct.
    # If non-leap and March 1, doy is 59 + 1 + 1 = 61. Correct.
    return doy

def is_leap(year):
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

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
# Use slice(min, max) but we must check if coords are increasing.
# The dataset print showed latitude: 53.5 ... 66.0 (increasing)
# longitude: 9.0 ... 30.0 (increasing)
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Time subset
t_start = pd.to_datetime(target_start_str)
t_end = pd.to_datetime(target_end_str)
b_start = pd.to_datetime(baseline_start_str)
b_end = pd.to_datetime(baseline_end_str)

# For baseline pools, we need [b_start - 5, b_end + 5]
b_pool_start = b_start - pd.Timedelta(days=5)
b_pool_end = b_end + pd.Timedelta(days=5)

# Load data into memory (float64 as requested for computation)
sst_target = ds_region.sel(time=slice(t_start, t_end)).analysed_sst.astype(np.float64).values
sst_baseline = ds_region.sel(time=slice(b_pool_start, b_pool_end)).analysed_sst.astype(np.float64).values

# Coordinate values
lat_vals = ds_region.latitude.values
lon_vals = ds_region.longitude.values
time_target_vals = ds_region.time.sel(time=slice(t_start, t_end)).values

print(f"SST Target shape: {sst_target.shape}")
print(f"SST Baseline shape: {sst_baseline.shape}")

# 1. Sea cells: SST is finite on every day of the target period
# sst_target is (time, lat, lon)
sea_mask = np.all(np.isfinite(sst_target), axis=0)
n_sea_cells = np.sum(sea_mask)
print(f"Number of sea cells: {n_sea_cells}")

# Baseline time coordinates
time_baseline_vals = ds_region.time.sel(time=slice(b_pool_start, b_pool_end)).values
baseline_dates = pd.to_datetime(time_baseline_vals)

# Precompute day of year and window maps for baseline
# We need a mapping: doy -> list of indices in sst_baseline
doy_to_indices = {d: [] for d in range(1, 367)}
for idx, dt in enumerate(baseline_dates):
    doy = get_doy(dt)
    # The prompt says "Day 60 gets no pool of its own." 
    # But Feb 29 values belong to neighbors' pools.
    # Our get_doy returns 60 for Feb 29.
    # We only care about dates that *are* a certain doy.
    if doy != 60:
        doy_to_indices[doy].append(idx)

# Now, for each doy d != 60, the pool is all SST values within +/- 5 days 
# of any date in the baseline period (1992-01-01 to 2002-12-31) that has doy d.
# Let's identify the baseline dates (1992-01-01 to 2002-12-31) first.
baseline_period_mask = (baseline_dates >= b_start) & (baseline_dates <= b_end)
baseline_period_indices = np.where(baseline_period_mask)[0]

# Re-calculate doy_to_indices but only for dates WITHIN the baseline period
doy_to_baseline_indices = {d: [] for d in range(1, 367)}
for idx in baseline_period_indices:
    dt = baseline_dates[idx]
    doy = get_doy(dt)
    if doy != 60:
        doy_to_baseline_indices[doy].append(idx)

# Now for each doy d != 60, find all indices in sst_baseline within +/- 5 days of these indices
doy_to_pool_indices = {d: [] for d in range(1, 367)}
for d in range(1, 367):
    if d == 60: continue
    pool_indices = set()
    for idx in doy_to_baseline_indices[d]:
        # Window: [idx-5, idx+5]
        for win_idx in range(idx - 5, idx + 6):
            if 0 <= win_idx < len(baseline_dates):
                pool_indices.add(win_idx)
    doy_to_pool_indices[d] = list(pool_indices)

# 2. Threshold and climatology
# We'll compute these for each cell.
# To speed up, we can iterate over sea cells.
# However, we can also vectorize over cells.
# sst_baseline is (time, lat, lon)
# For a fixed d, pool_indices is a list of time indices.
# sst_pool = sst_baseline[pool_indices, :, :]  # shape: (len(pool_indices), lat, lon)
# thresholds[d, :, :] = np.nanquantile(sst_pool, 0.9, axis=0, method='hazen')
# climatologies[d, :, :] = np.nanmean(sst_pool, axis=0)

thresholds = np.full((367, len(lat_vals), len(lon_vals)), np.nan, dtype=np.float64)
climatologies = np.full((367, len(lat_vals), len(lon_vals)), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60: continue
    pool_idx = doy_to_pool_indices[d]
    if not pool_idx: continue
    
    sst_pool = sst_baseline[pool_idx, :, :]
    # Vectorized quantile and mean over the time axis
    thresholds[d] = np.nanquantile(sst_pool, 0.9, axis=0, method='hazen')
    climatologies[d] = np.nanmean(sst_pool, axis=0)

# Handle day 60
thresholds[60] = (thresholds[59] + thresholds[61]) / 2
climatologies[60] = (climatologies[59] + climatologies[61]) / 2

# Smoothing: 31-day centered moving mean (wrap around)
def smooth_366(arr):
    # arr is (367, lat, lon), but we use index 1..366
    # result is (367, lat, lon)
    smoothed = np.full_like(arr)
    # We only smooth 1..366
    data = arr[1:] # (366, lat, lon)
    for d in range(366):
        # Window is d-15 to d+15 modulo 366
        # indices: (d-15)%366, ..., (d+15)%366
        window_indices = [(d + i) % 366 for i in range(-15, 16)]
        smoothed[d+1] = np.nanmean(data[window_indices], axis=0)
    return smoothed

thresholds_smooth = smooth_366(thresholds)
climatologies_smooth = smooth_366(climatologies)

# 3. Per-cell MHWs
# sst_target: (time, lat, lon)
# Threshold for each day in target period
target_doy = np.array([get_doy(dt) for dt in baseline_dates[0:0]]) # placeholder
# Wait, target_doy should be for the target period.
target_doy = np.array([get_doy(pd.to_datetime(dt)) for dt in time_target_vals])

# Hot days mask
# sst_target: (time, lat, lon)
# thresholds_smooth: (367, lat, lon)
# target_doy: (time,)
hot_mask = np.zeros(sst_target.shape, dtype=bool)
for t in range(len(target_doy)):
    d = target_doy[t]
    hot_mask[t] = sst_target[t] >= thresholds_smooth[d]

# Find per-cell MHWs
# This part is harder to vectorize. We'll do it cell by cell.
mhw_mask = np.zeros(sst_target.shape, dtype=np.uint8)

for lat_idx in range(len(lat_vals)):
    for lon_idx in range(len(lon_vals)):
        if not sea_mask[lat_idx, lon_idx]:
            continue
        
        hot_days = hot_mask[:, lat_idx, lon_idx]
        # Find runs of at least 5 consecutive hot days
        # and join runs separated by 1 or 2 non-hot days.
        
        # Initial runs
        in_mhw = np.zeros(len(hot_days), dtype=bool)
        
        # First pass: find runs of >= 5 hot days
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
            
        # Second pass: join runs separated by 1 or 2 non-hot days
        # "per-cell MHWs separated by 1 or 2 non-hot days are joined into one, 
        # and the gap days belong to it."
        # This must be repeated until no more joins are possible? 
        # Usually, "joining" is done once on the runs.
        
        changed = True
        while changed:
            changed = False
            # Find gaps of 1 or 2 non-hot days between MHW parts
            for t in range(1, len(hot_days) - 1):
                if not in_mhw[t]:
                    # Check for 1-day gap
                    if in_mhw[t-1] and in_mhw[t+1]:
                        in_mhw[t] = True
                        changed = True
                    # Check for 2-day gap
                    elif t < len(hot_days)-2 and in_mhw[t-1] and not in_mhw[t+1] and in_mhw[t+2]:
                        in_mhw[t] = True
                        in_mhw[t+1] = True
                        changed = True
        
        mhw_mask[:, lat_idx, lon_idx] = in_mhw.astype(np.uint8)

# 4. Regional events
# a day is active if at least one sea cell of the region is inside a per-cell MHW
active_days = np.any(mhw_mask == 1, axis=(1, 2))

# Regional MHW event is a maximal run of consecutive active days
regional_events = []
in_event = False
onset = None

for t in range(len(active_days)):
    if active_days[t] and not in_event:
        in_event = True
        onset = time_target_vals[t]
    elif not active_days[t] and in_event:
        in_event = False
        regional_events.append({"onset": pd.to_datetime(onset).strftime('%Y-%m-%d'), 
                                "end": pd.to_datetime(time_target_vals[t-1]).strftime('%Y-%m-%d')})

if in_event:
    regional_events.append({"onset": pd.to_datetime(onset).strftime('%Y-%m-%d'), 
                            "end": pd.to_datetime(time_target_vals[-1]).strftime('%Y-%m-%d')})

# Write results
import os
os.makedirs('output', exist_ok=True)

# mhw_mask.nc
ds_out = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={"time": time_target_vals, "latitude": lat_vals, "longitude": lon_vals}
)
# Rename latitude/longitude to lat/lon for the file as requested? 
# "dimensions (time, lat, lon)". 
# The prompt says "write it with the dataset's coordinate values". 
# The dataset uses latitude/longitude. I will rename them to lat/lon for the final NC if required, 
# but the dimensions names should be exactly as requested.
ds_out = ds_out.rename({"latitude": "lat", "longitude": "lon"})
ds_out.to_netcdf("output/mhw_mask.nc")

# report.json
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
