
import xarray as xr
import numpy as np
import pandas as pd
import json
import os

# =====================================================
# FULL PIPELINE
# =====================================================

# Load dataset
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Region bounds
lat_min, lat_max = 63.31, 64.51
lon_min, lon_max = 21.31, 22.51

# Get region indices
lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
lat_indices = np.where((lat_vals >= lat_min) & (lat_vals <= lat_max))[0]
lon_indices = np.where((lon_vals >= lon_min) & (lon_vals <= lon_max))[0]

region_lat = lat_vals[lat_indices].astype(np.float64)
region_lon = lon_vals[lon_indices].astype(np.float64)
n_lat = len(region_lat)
n_lon = len(region_lon)

# Target period
target_start = pd.Timestamp('2004-06-01')
target_end = pd.Timestamp('2004-08-31')
target_dates = pd.date_range(target_start, target_end, freq='D')

# Baseline data period (with windows)
data_start = pd.Timestamp('1991-12-27')
data_end = pd.Timestamp('2003-01-05')

# Get time indices
times = pd.DatetimeIndex(ds.time.values)
baseline_time_mask = (times >= data_start) & (times <= data_end)
baseline_time_idx = np.where(baseline_time_mask)[0]
target_time_mask = (times >= target_start) & (times <= target_end)
target_time_idx = np.where(target_time_mask)[0]

# Extract data
baseline_data = ds['analysed_sst'].isel(
    time=baseline_time_idx,
    latitude=slice(lat_indices[0], lat_indices[-1]+1),
    longitude=slice(lon_indices[0], lon_indices[-1]+1)
).values.astype(np.float64)

target_data = ds['analysed_sst'].isel(
    time=target_time_idx,
    latitude=slice(lat_indices[0], lat_indices[-1]+1),
    longitude=slice(lon_indices[0], lon_indices[-1]+1)
).values.astype(np.float64)

# Sea cells
sea_cells = np.all(np.isfinite(target_data), axis=0)

# Day of year function
def doy(month, day):
    offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return offsets[month-1] + day

def date_to_doy(dt):
    return doy(dt.month, dt.day)

# Baseline period
baseline_start = pd.Timestamp('1992-01-01')
baseline_end = pd.Timestamp('2002-12-31')
baseline_dates = pd.date_range(baseline_start, baseline_end, freq='D')

# Extended data period dates
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
n_doy = 366
thresholds = np.zeros((n_lat, n_lon, n_doy))
climatology = np.zeros((n_lat, n_lon, n_doy))

sea_cell_indices = np.argwhere(sea_cells)

for d in range(1, 367):
    if d == 60:
        continue
    
    positions = pool_positions[d]
    pool_data = baseline_data[positions]
    
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

# Smooth
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

# Check if hot
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
        
        # Find runs
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
        
        # Filter >= 5
        mhw_runs = [r for r in runs if (r[1] - r[0] + 1) >= 5]
        
        # Join gaps of 1-2 days
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
        
        # Mark
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
event_list = []
for start, end in events:
    onset = target_dates[start].strftime('%Y-%m-%d')
    end_date = target_dates[end].strftime('%Y-%m-%d')
    event_list.append({"onset": onset, "end": end_date})
    print(f"  {onset} to {end_date}")

# =====================================================
# WRITE OUTPUT FILES
# =====================================================

os.makedirs('/work/output', exist_ok=True)

# Write mhw_mask.nc
# Create xarray dataset with coordinates from the original dataset
time_coords = ds.time.values[target_time_idx]
lat_coords = ds.latitude.values[lat_indices]
lon_coords = ds.longitude.values[lon_indices]

ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': time_coords,
        'lat': lat_coords,
        'lon': lon_coords,
    }
)

ds_out.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf')
print("Wrote mhw_mask.nc")

# Write report.json
report = {
    "region": {
        "lat_min": float(lat_min),
        "lat_max": float(lat_max),
        "lon_min": float(lon_min),
        "lon_max": float(lon_max)
    },
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": "2004-06-01",
        "end": "2004-08-31"
    },
    "events": event_list,
    "complete": True,
    "caveats": ""
}

with open('/work/output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Wrote report.json")
print("\nReport:")
print(json.dumps(report, indent=2))
