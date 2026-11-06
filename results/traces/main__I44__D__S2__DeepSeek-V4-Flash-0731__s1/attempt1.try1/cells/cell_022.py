
import xarray as xr
import numpy as np
import pandas as pd
import json
import os

# =====================================================
# STEP 2: Threshold and climatology computation
# =====================================================

# Day of year function (1-366)
def doy(month, day):
    offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return offsets[month-1] + day

def date_to_doy(dt):
    return doy(dt.month, dt.day)

# Load data (reloaded from saved files for consistency)
baseline_data = np.load('/work/baseline_data.npy')
target_data = np.load('/work/target_data.npy')
sea_cells = np.load('/work/sea_cells.npy')

# Baseline period
baseline_start = pd.Timestamp('1992-01-01')
baseline_end = pd.Timestamp('2002-12-31')
baseline_dates = pd.date_range(baseline_start, baseline_end, freq='D')

# Extended data period
data_start = pd.Timestamp('1991-12-27')
data_end = pd.Timestamp('2003-01-05')
data_dates = pd.date_range(data_start, data_end, freq='D')

# Build pool dates for each day of year
pool_dates = {}
for d in range(1, 367):
    if d == 60:
        continue
    base_dates_d = [dt for dt in baseline_dates if date_to_doy(dt) == d]
    pool = set()
    for t0 in base_dates_d:
        for offset in range(-5, 6):
            t = t0 + pd.Timedelta(days=offset)
            if data_start <= t <= data_end:
                pool.add(t)
    pool_dates[d] = sorted(pool)

# Map date to position in baseline_data
date_to_pos = {dt: i for i, dt in enumerate(data_dates)}

# Get pool positions
pool_positions = {}
for d in range(1, 367):
    if d == 60:
        continue
    pool_positions[d] = [date_to_pos[dt] for dt in pool_dates[d]]

# Compute thresholds and climatology
n_lat, n_lon = sea_cells.shape
n_doy = 366

thresholds = np.zeros((n_lat, n_lon, n_doy))
climatology = np.zeros((n_lat, n_lon, n_doy))

sea_cell_indices = np.argwhere(sea_cells)

# For each doy, gather pool data and compute stats for sea cells
for d in range(1, 367):
    if d == 60:
        continue
    
    positions = pool_positions[d]
    pool_data = baseline_data[positions]  # (n_pool, n_lat, n_lon)
    
    for lat_i, lon_i in sea_cell_indices:
        values = pool_data[:, lat_i, lon_i]
        valid = values[np.isfinite(values)]
        if len(valid) > 0:
            thresholds[lat_i, lon_i, d-1] = np.percentile(valid, 90, method='hazen')
            climatology[lat_i, lon_i, d-1] = np.mean(valid)
        else:
            thresholds[lat_i, lon_i, d-1] = np.nan
            climatology[lat_i, lon_i, d-1] = np.nan

# Set day 60 (index 59) = mean of days 59 (index 58) and 61 (index 60)
thresholds[sea_cell_indices[:, 0], sea_cell_indices[:, 1], 59] = (
    thresholds[sea_cell_indices[:, 0], sea_cell_indices[:, 1], 58] + 
    thresholds[sea_cell_indices[:, 0], sea_cell_indices[:, 1], 60]
) / 2

climatology[sea_cell_indices[:, 0], sea_cell_indices[:, 1], 59] = (
    climatology[sea_cell_indices[:, 0], sea_cell_indices[:, 1], 58] + 
    climatology[sea_cell_indices[:, 0], sea_cell_indices[:, 1], 60]
) / 2

# Smooth with 31-day centered moving mean wrapping around the year
def smooth_wrap(arr):
    n = arr.shape[-1]
    assert n == 366
    result = np.zeros_like(arr)
    for i in range(n):
        indices = [(i + offset) % n for offset in range(-15, 16)]
        result[..., i] = np.mean(arr[..., indices], axis=-1)
    return result

thresholds_smooth = smooth_wrap(thresholds)
climatology_smooth = smooth_wrap(climatology)

print("Threshold and climatology computed and smoothed")

# =====================================================
# STEP 3: Per-cell MHWs
# =====================================================

# Target doys
target_doys = np.array([date_to_doy(dt) for dt in target_dates])

# Check if hot: SST >= threshold
n_time = len(target_dates)
hot = np.zeros((n_time, n_lat, n_lon), dtype=bool)

for t in range(n_time):
    d_idx = target_doys[t] - 1
    thresh = thresholds_smooth[:, :, d_idx]
    hot[t] = target_data[t] >= thresh

# Find per-cell MHWs
mhw_mask = np.zeros((n_time, n_lat, n_lon), dtype=np.uint8)

for lat_i in range(n_lat):
    for lon_i in range(n_lon):
        if not sea_cells[lat_i, lon_i]:
            continue
        
        hot_cell = hot[:, lat_i, lon_i]
        
        # Find runs of hot days
        runs = []
        in_run = False
        run_start = 0
        for t in range(n_time):
            if hot_cell[t] and not in_run:
                in_run = True
                run_start = t
            elif not hot_cell[t] and in_run:
                in_run = False
                runs.append((run_start, t-1))
        if in_run:
            runs.append((run_start, n_time-1))
        
        # Filter runs of >= 5 consecutive hot days
        mhw_runs = [r for r in runs if (r[1] - r[0] + 1) >= 5]
        
        # Join runs separated by 1-2 non-hot days
        if len(mhw_runs) > 1:
            joined = []
            current = mhw_runs[0]
            for next_run in mhw_runs[1:]:
                gap = next_run[0] - current[1] - 1
                if gap <= 2:
                    current = (current[0], next_run[1])
                else:
                    joined.append(current)
                    current = next_run
            joined.append(current)
            mhw_runs = joined
        
        # Mark mask
        for run_start, run_end in mhw_runs:
            mhw_mask[run_start:run_end+1, lat_i, lon_i] = 1

print(f"MHW mask: {mhw_mask.sum()} cell-days in MHWs")

# =====================================================
# STEP 4: Regional events
# =====================================================

# A day is active if at least one sea cell is inside a per-cell MHW
active = np.zeros(n_time, dtype=bool)
for t in range(n_time):
    active[t] = np.any(mhw_mask[t][sea_cells] == 1)

print(f"Active days: {active.sum()}")

# Find maximal runs of consecutive active days
events = []
in_event = False
event_start = 0
for t in range(n_time):
    if active[t] and not in_event:
        in_event = True
        event_start = t
    elif not active[t] and in_event:
        in_event = False
        events.append((event_start, t-1))
if in_event:
    events.append((event_start, n_time-1))

print(f"Regional events: {len(events)}")
for start, end in events:
    print(f"  {target_dates[start].date()} to {target_dates[end].date()}")

# Save intermediate results
np.save('/work/mhw_mask_final.npy', mhw_mask)
np.save('/work/hot_final.npy', hot)
print("Intermediate results saved")
