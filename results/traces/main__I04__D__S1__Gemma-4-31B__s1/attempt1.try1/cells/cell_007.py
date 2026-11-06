import fsspec
import xarray as xr
import numpy as np
import pandas as pd
import json

# Parameters
lat_min, lat_max = 54.39, 55.59
lon_min, lon_max = 18.25, 19.45
target_start = '2020-06-01'
target_end = '2020-08-31'
baseline_start = '1992-01-01'
baseline_end = '2002-12-31'
# To cover the +/- 5 days window around baseline dates
data_start = '1991-12-27'
data_end = '2003-01-05'

fs = fsspec.filesystem('onedata')
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
fs.get(remote_path, local_path)

# Open dataset
ds = xr.open_dataset(local_path, engine="h5netcdf")

# Subset region
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Subset time
# We need baseline windows and target period
t_baseline = ds_region.sel(time=slice(data_start, data_end))
t_target = ds_region.sel(time=slice(target_start, target_end))

# Close original ds to save memory
ds.close()

# Use double precision for calculations
sst_baseline = t_baseline.analysed_sst.astype(np.float64)
sst_target = t_target.analysed_sst.astype(np.float64)

# Function to map date to doy (1-366)
def get_doy(dt):
    # Use a leap year as reference for doy
    ref_date = pd.Timestamp('2000-01-01')
    # But this is tricky. Let's just use:
    # if month < 2: doy = day
    # if month == 2: doy = 31 + day
    # if month > 2: doy = (day of year in leap year)
    # Actually, a simpler way:
    # doy = dt.timetuple().tm_yday
    # if not leap and month > 2: doy += 1
    
    year = dt.year
    month = dt.month
    day = dt.day
    
    if month == 1:
        return day
    if month == 2:
        return 31 + day
    
    # For month > 2, use leap year doy
    # pandas Timedelta from Jan 1 of leap year
    # Or just use a fixed leap year date:
    temp_date = pd.Timestamp(year=2000, month=month, day=day)
    return temp_date.dayofyear

# Apply get_doy to all times
baseline_times = pd.to_datetime(sst_baseline.time.values)
baseline_doys = np.array([get_doy(t) for t in baseline_times])

target_times = pd.to_datetime(sst_target.time.values)
target_doys = np.array([get_doy(t) for t in target_times])

# 1. Sea cells: SST finite on every day of target period
# sst_target has shape (time, lat, lon)
is_finite = np.all(np.isfinite(sst_target.values), axis=0)
sea_cells_mask = is_finite

# 2. Threshold and Climatology
# We need a pool for each doy d in 1..366 (d != 60)
# The pool P_d = { SST(t') | there exists t in [baseline_start, baseline_end] with doy(t)=d and |t-t'| <= 5 }

# Pre-calculate the mapping from doy to all dates in the baseline period
baseline_dates_range = pd.date_range(baseline_start, baseline_end)
doy_to_baseline_dates = {}
for dt in baseline_dates_range:
    d = get_doy(dt)
    if d == 60: continue
    if d not in doy_to_baseline_dates:
        doy_to_baseline_dates[d] = []
    doy_to_baseline_dates[d].append(dt)

# Pre-calculate the pools for each doy
# Since we only care about sea cells, we can work with sea cells only
# but it's easier to work with the whole grid if it fits.
# Let's find the sea cells' indices
lat_indices, lon_indices = np.where(sea_cells_mask)
num_sea_cells = len(lat_indices)

# We'll store thresholds and climatology as arrays of shape (366, lat, lon)
thresholds = np.full((367, sst_baseline.latitude.size, sst_baseline.longitude.size), np.nan, dtype=np.float64)
climatology = np.full((367, sst_baseline.latitude.size, sst_baseline.longitude.size), np.nan, dtype=np.float64)

# All dates in the sst_baseline dataset
all_baseline_times = pd.to_datetime(sst_baseline.time.values)

# For each doy d != 60
for d in range(1, 367):
    if d == 60:
        continue
    
    # Find all t' in the baseline dataset that are within 5 days of any t in [baseline_start, baseline_end] with doy(t)=d
    # This can be a large set of dates.
    # Let's optimize: find all such t' first.
    
    dates_in_baseline_with_d = doy_to_baseline_dates.get(d, [])
    if not dates_in_baseline_with_d:
        continue
        
    # The union of [t-5, t+5] for all t in dates_in_baseline_with_d
    # We can just check all t' in all_baseline_times
    
    # To optimize, let's use the fact that the baseline dates are sorted.
    # But baseline_dates_range is sorted.
    # The pool of dates t' is:
    # For each year y in 1992..2002:
    #   t_y is the date with doy d in year y.
    #   t'_y is the range [t_y-5, t_y+5].
    
    # Instead of looping over all t', let's find the indices in all_baseline_times.
    pool_indices = []
    for t in dates_in_baseline_with_d:
        # Find indices of all_baseline_times in [t-5, t+5]
        # Since all_baseline_times is sorted:
        start_t = t - pd.Timedelta(days=5)
        end_t = t + pd.Timedelta(days=5)
        # Find indices using searchsorted
        idx_start = np.searchsorted(all_baseline_times, start_t)
        idx_end = np.searchsorted(all_baseline_times, end_t, side='right')
        pool_indices.extend(range(idx_start, idx_end))
    
    pool_indices = sorted(list(set(pool_indices)))
    
    if not pool_indices:
        continue
        
    # SST values for these indices: shape (len(pool_indices), lat, lon)
    pool_sst = sst_baseline.values[pool_indices, :, :]
    
    # Threshold: 90th percentile (method="hazen")
    # np.quantile(pool_sst, 0.9, axis=0, method="hazen")
    thresholds[d] = np.nanquantile(pool_sst, 0.9, axis=0, method="hazen")
    # Climatology: Mean
    climatology[d] = np.nanmean(pool_sst, axis=0)

# Handle day 60: mean of 59 and 61
thresholds[60] = (thresholds[59] + thresholds[61]) / 2.0
climatology[60] = (climatology[59] + climatology[61]) / 2.0

# Smoothing: 31-day centred moving mean (wrap around)
def smooth_31(arr):
    # arr shape (367, lat, lon)
    # We only use indices 1..366
    data = arr[1:] # (366, lat, lon)
    smoothed = np.full_like(data, np.nan)
    
    for d in range(366):
        # indices d-15 to d+15 modulo 366
        # In python, % 366 handles negative numbers correctly: -1 % 366 = 365
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = data[indices, :, :]
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

smoothed_thresholds = smooth_31(thresholds)
smoothed_climatology = smooth_31(climatology)

# 3. Per-cell MHWs
# target_doys: doy for each day in target period
# sst_target: (time, lat, lon)
# smoothed_thresholds: (366, lat, lon)

hot_days = np.zeros(sst_target.shape, dtype=bool)
for t_idx, d in enumerate(target_doys):
    # d is 1..366
    # smoothed_thresholds is indexed 0..365, so d-1
    hot_days[t_idx] = sst_target.values[t_idx] >= smoothed_thresholds[d-1]

# For each cell, find MHWs
# A per-cell MHW: >= 5 consecutive hot days, joined by 1-2 non-hot days.
mhw_mask = np.zeros(hot_days.shape, dtype=np.uint8)

lat_size = sst_target.latitude.size
lon_size = sst_target.longitude.size

for i in range(lat_size):
    for j in range(lon_size):
        if not sea_cells_mask[i, j]:
            continue
        
        cell_hot = hot_days[:, i, j]
        # Find runs of hot days
        # A simple way:
        # 1. Find all runs of at least 5 hot days
        # 2. Join them if gap <= 2
        
        # We can use a simple state machine or identify runs
        # Let's use a boolean array for MHW
        cell_mhw = np.zeros(len(cell_hot), dtype=bool)
        
        # First, identify all runs of 5+ hot days
        run_start = -1
        for t in range(len(cell_hot)):
            if cell_hot[t]:
                if run_start == -1:
                    run_start = t
            else:
                if run_start != -1:
                    if t - run_start >= 5:
                        cell_mhw[run_start:t] = True
                    run_start = -1
        if run_start != -1:
            if len(cell_hot) - run_start >= 5:
                cell_mhw[run_start:] = True
                
        # Now join gaps of 1 or 2 non-hot days
        # Repeat until no more joins are possible
        while True:
            changed = False
            # Look for gaps of 1 or 2 non-hot days between MHW segments
            # Since the target period is short (92 days), we can just loop
            for t in range(1, len(cell_mhw) - 1):
                if not cell_mhw[t]:
                    # Check if it's a gap of 1
                    if cell_mhw[t-1] and cell_mhw[t+1]:
                        cell_mhw[t] = True
                        changed = True
            for t in range(1, len(cell_mhw) - 2):
                if not cell_mhw[t] and not cell_mhw[t+1]:
                    # Check if it's a gap of 2
                    if cell_mhw[t-1] and cell_mhw[t+2]:
                        cell_mhw[t] = True
                        cell_mhw[t+1] = True
                        changed = True
            if not changed:
                break
        
        mhw_mask[:, i, j] = cell_mhw.astype(np.uint8)

# 4. Regional events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
event_start = -1
for t in range(len(active_days)):
    if active_days[t]:
        if event_start == -1:
            event_start = t
    else:
        if event_start != -1:
            regional_events.append((event_start, t-1))
            event_start = -1
if event_start != -1:
    regional_events.append((event_start, len(active_days)-1))

# Prepare outputs
import os
os.makedirs('output', exist_ok=True)

# NetCDF output
# Create xarray dataset
ds_mhw = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": t_target.time,
        "latitude": t_target.latitude,
        "longitude": t_target.longitude,
    },
)
ds_mhw.to_netcdf('output/mhw_mask.nc')

# JSON report
events_list = []
for start_idx, end_idx in regional_events:
    onset = target_times[start_idx].strftime('%Y-%m-%d')
    end = target_times[end_idx].strftime('%Y-%m-%d')
    events_list.append({"onset": onset, "end": end})

# Baseline analysed dates
baseline_analysed_start = all_baseline_times[0].strftime('%Y-%m-%d')
baseline_analysed_end = all_baseline_times[-1].strftime('%Y-%m-%d')

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": baseline_analysed_start, "end": baseline_analysed_end},
    "target_analysed": {
        "start": target_times[0].strftime('%Y-%m-%d'),
        "end": target_times[-1].strftime('%Y-%m-%d')
    },
    "events": events_list,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Done")
