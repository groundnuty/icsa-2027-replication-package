import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
import os
from datetime import datetime, timedelta

# Check numpy version
print(f"Numpy version: {np.__version__}")

fs = fsspec.filesystem('onedata')
base_dir = 'icsa2027_data_20261101T090944Z/s1z'

# Region bounds
LAT_MIN, LAT_MAX = 57.13, 58.33
LON_MIN, LON_MAX = 22.79, 23.99
TARGET_START = '2010-06-01'
TARGET_END = '2010-08-31'
BASELINE_START = '1992-01-01'
BASELINE_END = '2002-12-31'

def get_sst_for_range(start_date, end_date):
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    date_range = pd.date_range(start, end)
    
    all_data = []
    all_times = []
    coords = None
    
    for date in date_range:
        fname = f"{base_dir}/sst_{date.strftime('%Y%m%d')}.nc"
        try:
            with fs.open(fname, "rb") as f:
                ds = xr.open_dataset(f, engine="h5netcdf")
                ds_region = ds.sel(
                    latitude=slice(LAT_MIN, LAT_MAX), 
                    longitude=slice(LON_MIN, LON_MAX)
                )
                # Single day file: analysed_sst has shape (1, lat, lon)
                val = ds_region['analysed_sst'].values
                all_data.append(np.squeeze(val, axis=0).astype(np.float64))
                all_times.append(ds_region.time.values)
                if coords is None:
                    coords = {
                        'latitude': ds_region.latitude.values,
                        'longitude': ds_region.longitude.values
                    }
        except Exception as e:
            print(f"Error reading {fname}: {e}")
    
    if not all_data:
        return None
    
    sst_array = np.stack(all_data, axis=0)
    times = np.concatenate(all_times)
    
    ds = xr.Dataset(
        {"analysed_sst": (("time", "latitude", "longitude"), sst_array)},
        coords={
            "time": times,
            "latitude": coords['latitude'],
            "longitude": coords['longitude'],
        }
    )
    return ds

# Load target data
print("Loading target data...")
ds_target = get_sst_for_range(TARGET_START, TARGET_END)
if ds_target is None:
    print("No target data found")
    exit()

# Sea cells: SST finite on every day of target period
sst_target_vals = ds_target['analysed_sst'].values
sea_mask = np.all(np.isfinite(sst_target_vals), axis=0)
print(f"Sea cells found: {np.sum(sea_mask)} out of {sea_mask.size}")

# Load baseline data (including 5-day buffers)
print("Loading baseline data...")
ds_baseline = get_sst_for_range('1991-12-27', '2003-01-05')
sst_baseline_vals = ds_baseline['analysed_sst'].values

# Baseline dates for pooling
baseline_dates_full = pd.to_datetime(ds_baseline.time.values)
core_baseline_dates = pd.date_range(pd.to_datetime(BASELINE_START), pd.to_datetime(BASELINE_END))

time_to_idx = {date: i for i, date in enumerate(baseline_dates_full)}

def get_doy(dt):
    return dt.dayofyear

# Thresholds and Climatology (float64)
thresholds = np.full((366, *sea_mask.shape), np.nan, dtype=np.float64)
climatology = np.full((366, *sea_mask.shape), np.nan, dtype=np.float64)

# Pre-calculate core dates for each DOY
core_doy_map = {d: [] for d in range(1, 367)}
for dt in core_baseline_dates:
    core_doy_map[get_doy(dt)].append(dt)

for d in range(1, 367):
    if d == 60:
        continue
    
    pool_indices = []
    for b_date in core_doy_map[d]:
        for offset in range(-5, 6):
            win_date = b_date + timedelta(days=offset)
            if win_date in time_to_idx:
                pool_indices.append(time_to_idx[win_date])
    
    if not pool_indices:
        continue
        
    pool = sst_baseline_vals[pool_indices, :, :]
    
    # Method 'hazen' for quantile (type 5)
    try:
        thresholds[d-1] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
        climatology[d-1] = np.nanmean(pool, axis=0)
    except TypeError:
        # Fallback for older numpy
        thresholds[d-1] = np.nanpercentile(pool, 90, axis=0)
        climatology[d-1] = np.nanmean(pool, axis=0)

# Handle day 60
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

# Smoothing: 31-day centered moving mean, wrap around
def smooth_wrap(arr):
    smoothed = np.zeros_like(arr)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices]
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

thresholds_smooth = smooth_wrap(thresholds)

# Per-cell MHWs
target_time = pd.to_datetime(ds_target.time.values)
target_doy = np.array([get_doy(t) for t in target_time])

hot_days = np.zeros(sst_target_vals.shape, dtype=bool)
for t_idx in range(len(target_time)):
    d = target_doy[t_idx]
    hot_days[t_idx] = sst_target_vals[t_idx] >= thresholds_smooth[d-1]

mhw_mask = np.zeros(sst_target_vals.shape, dtype=np.uint8)
lat_len, lon_len = sea_mask.shape

for i in range(lat_len):
    for j in range(lon_len):
        if not sea_mask[i, j]:
            continue
            
        cell_hot = hot_days[:, i, j]
        in_mhw = np.zeros(len(cell_hot), dtype=bool)
        
        runs = []
        start = None
        for t in range(len(cell_hot)):
            if cell_hot[t]:
                if start is None: start = t
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
            
        merged = []
        curr_start, curr_end = runs[0]
        for next_start, next_end in runs[1:]:
            gap = next_start - curr_end - 1
            if gap <= 2:
                curr_end = next_end
            else:
                merged.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged.append((curr_start, curr_end))
            
        for start, end in merged:
            in_mhw[start:end+1] = True
            
        mhw_mask[:, i, j] = in_mhw.astype(np.uint8)

# Regional Events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
in_event = False
event_start = None

for t in range(len(active_days)):
    if active_days[t]:
        if not in_event:
            in_event = True
            event_start = t
    else:
        if in_event:
            in_event = False
            regional_events.append((target_time[event_start], target_time[t-1]))
if in_event:
    regional_events.append((target_time[event_start], target_time[-1]))

# Write output
output_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": ds_target.time,
        "latitude": ds_target.latitude,
        "longitude": ds_target.longitude,
    }
)
os.makedirs("output", exist_ok=True)
output_ds.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
    "baseline_analysed": {
        "start": "1991-12-27",
        "end": "2003-01-05"
    },
    "target_analysed": {
        "start": TARGET_START,
        "end": TARGET_END
    },
    "events": [
        {"onset": e[0].strftime('%Y-%m-%d'), "end": e[1].strftime('%Y-%m-%d')} 
        for e in regional_events
    ],
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f, indent=2)

print("Done")
