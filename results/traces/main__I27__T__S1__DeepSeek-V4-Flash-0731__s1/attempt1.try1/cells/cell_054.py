
import numpy as np
import pandas as pd
import xarray as xr
import fsspec
import json
import datetime
import os

# ============================================================
# CONFIGURATION
# ============================================================
REGION = {
    "lat_min": 57.83,
    "lat_max": 59.03,
    "lon_min": 17.41,
    "lon_max": 18.61,
}
TARGET_START = '2008-06-01'
TARGET_END = '2008-08-31'
BASELINE_START = '1992-01-01'
BASELINE_END = '2002-12-31'
# Full data range needed (with ±5 day window extensions)
DATA_START = '1991-12-27'
DATA_END = '2003-01-05'

# ============================================================
# DAY-OF-YEAR MAPPING (fixed 366-day calendar)
# ============================================================
def date_to_doy(dt):
    """Map a date to day-of-year 1-366 using the fixed calendar (Feb=29)."""
    days_in_month_fixed = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month_fixed[:dt.month]) + dt.day

# ============================================================
# LOAD DATA
# ============================================================
print("Loading data...")
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Select region
region = ds.sel(
    latitude=slice(REGION["lat_min"], REGION["lat_max"]),
    longitude=slice(REGION["lon_min"], REGION["lon_max"])
)

# Extract baseline and target data
baseline_ds = region.sel(time=slice(DATA_START, DATA_END))
target_ds = region.sel(time=slice(TARGET_START, TARGET_END))

# Convert to float64
baseline_data = baseline_ds.analysed_sst.values.astype(np.float64)
target_data = target_ds.analysed_sst.values.astype(np.float64)
baseline_times = pd.DatetimeIndex(baseline_ds.time.values)
target_times = pd.DatetimeIndex(target_ds.time.values)
lat_coords = region.latitude.values
lon_coords = region.longitude.values

print(f"Baseline: {baseline_times[0].date()} to {baseline_times[-1].date()}, n={len(baseline_times)}")
print(f"Target: {target_times[0].date()} to {target_times[-1].date()}, n={len(target_times)}")
print(f"Region shape: {baseline_data.shape[1:]}")

n_lat, n_lon = baseline_data.shape[1], baseline_data.shape[2]
n_time_target = len(target_times)

# ============================================================
# STEP 1: SEA CELLS
# ============================================================
print("\nStep 1: Identifying sea cells...")
sea_mask = np.all(~np.isnan(target_data), axis=0)  # (n_lat, n_lon)
n_sea = sea_mask.sum()
print(f"Sea cells: {n_sea} out of {n_lat * n_lon}")

# ============================================================
# STEP 2: THRESHOLD AND CLIMATOLOGY
# ============================================================
print("\nStep 2: Computing thresholds and climatology...")

# Build pool indices for each day of year
all_baseline_dates = [pd.Timestamp(t) for t in baseline_times]
date_to_idx = {d: i for i, d in enumerate(all_baseline_dates)}
baseline_start_ts = pd.Timestamp(BASELINE_START)
baseline_end_ts = pd.Timestamp(BASELINE_END)

# For each doy (1-366, except 60), find the pool indices
pool_indices_by_doy = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    window_dates = set()
    for date in all_baseline_dates:
        if baseline_start_ts <= date <= baseline_end_ts and date_to_doy(date) == doy:
            for delta in range(-5, 6):
                window_date = date + pd.Timedelta(days=delta)
                if window_date in date_to_idx:
                    window_dates.add(date_to_idx[window_date])
    pool_indices_by_doy[doy] = sorted(window_dates)

# Initialize threshold and climatology arrays (index d-1 = doy d)
threshold_raw = np.full((n_lat, n_lon, 366), np.nan)
clim_raw = np.full((n_lat, n_lon, 366), np.nan)

# Compute for all doy except 60
for doy in range(1, 367):
    if doy == 60:
        continue
    idx = doy - 1
    pool_idx = pool_indices_by_doy[doy]
    n_pool = len(pool_idx)
    pool_flat = baseline_data[pool_idx].reshape(n_pool, -1)
    
    q90 = np.nanpercentile(pool_flat, 90, axis=0, method='hazen')
    mean_val = np.nanmean(pool_flat, axis=0)
    
    threshold_raw[:, :, idx] = q90.reshape(n_lat, n_lon)
    clim_raw[:, :, idx] = mean_val.reshape(n_lat, n_lon)

# Day 60 = mean of days 59 and 61 (indices 58 and 60)
threshold_raw[:, :, 59] = (threshold_raw[:, :, 58] + threshold_raw[:, :, 60]) / 2.0
clim_raw[:, :, 59] = (clim_raw[:, :, 58] + clim_raw[:, :, 60]) / 2.0

# Smooth with 31-day centered moving mean wrapping around
print("Smoothing...")
def smooth_31(arrays):
    result = np.zeros_like(arrays)
    for d in range(366):
        indices = [(d + offset) % 366 for offset in range(-15, 16)]
        result[..., d] = np.nanmean(arrays[..., indices], axis=-1)
    return result

threshold_smooth = smooth_31(threshold_raw)
clim_smooth = smooth_31(clim_raw)
print("Smoothing complete")

# ============================================================
# STEP 3: PER-CELL MHWs
# ============================================================
print("\nStep 3: Detecting per-cell MHWs...")

# Map each target date to day-of-year index (0-based)
target_doy_idx = np.array([date_to_doy(pd.Timestamp(t)) - 1 for t in target_times])

# Get threshold for each target day
threshold_for_target = np.zeros((n_time_target, n_lat, n_lon), dtype=np.float64)
for i in range(n_time_target):
    threshold_for_target[i] = threshold_smooth[:, :, target_doy_idx[i]]

# Hot days
hot = target_data >= threshold_for_target  # (n_time_target, n_lat, n_lon)
hot = hot & sea_mask[np.newaxis, :, :]  # Only sea cells can be hot

# Per-cell MHWs
mhw = np.zeros_like(hot, dtype=bool)

for lat_i, lon_i in np.argwhere(sea_mask):
    hot_series = hot[:, lat_i, lon_i]
    
    # Find runs of consecutive hot days
    runs = []
    in_run = False
    start = 0
    for i in range(n_time_target):
        if hot_series[i] and not in_run:
            start = i
            in_run = True
        elif not hot_series[i] and in_run:
            runs.append((start, i - 1))
            in_run = False
    if in_run:
        runs.append((start, n_time_target - 1))
    
    # Filter to runs of >= 5 days
    long_runs = [(s, e) for s, e in runs if e - s + 1 >= 5]
    
    # Join runs separated by 1-2 non-hot days
    if long_runs:
        joined_runs = [long_runs[0]]
        for run in long_runs[1:]:
            prev_s, prev_e = joined_runs[-1]
            gap = run[0] - prev_e - 1
            if 1 <= gap <= 2:
                joined_runs[-1] = (prev_s, run[1])
            else:
                joined_runs.append(run)
        
        # Mark MHW days
        for s, e in joined_runs:
            mhw[s:e+1, lat_i, lon_i] = True

n_mhw_days = mhw.sum()
print(f"Per-cell MHW days: {n_mhw_days}")

# ============================================================
# STEP 4: REGIONAL EVENTS
# ============================================================
print("\nStep 4: Identifying regional events...")

# Day active if at least one sea cell is in an MHW
active = np.any(mhw, axis=(1, 2))  # (n_time_target,)

# Find maximal runs of consecutive active days
events = []
in_event = False
start = 0
for i in range(n_time_target):
    if active[i] and not in_event:
        start = i
        in_event = True
    elif not active[i] and in_event:
        events.append((start, i - 1))
        in_event = False
if in_event:
    events.append((start, n_time_target - 1))

event_list = []
for s, e in events:
    onset = str(target_times[s].date())
    end = str(target_times[e].date())
    event_list.append({"onset": onset, "end": end})
    print(f"  Event: {onset} to {end}, duration={e-s+1} days")

# ============================================================
# WRITE OUTPUT FILES
# ============================================================
print("\nWriting output files...")

# Write mhw_mask.nc
mhw_uint8 = mhw.astype(np.uint8)  # (n_time_target, n_lat, n_lon)

# Create xarray dataset
ds_out = xr.Dataset(
    {
        "mhw": (("time", "lat", "lon"), mhw_uint8),
    },
    coords={
        "time": target_ds.time.values,
        "lat": lat_coords,
        "lon": lon_coords,
    },
)
ds_out.mhw.attrs['long_name'] = 'Marine heatwave mask'
ds_out.mhw.attrs['units'] = '1 = inside per-cell MHW, 0 = not inside'

ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc written")

# Write report.json
report = {
    "region": {
        "lat_min": REGION["lat_min"],
        "lat_max": REGION["lat_max"],
        "lon_min": REGION["lon_min"],
        "lon_max": REGION["lon_max"],
    },
    "baseline_analysed": {
        "start": str(baseline_times[0].date()),
        "end": str(baseline_times[-1].date()),
    },
    "target_analysed": {
        "start": TARGET_START,
        "end": TARGET_END,
    },
    "events": event_list,
    "complete": True,
    "caveats": "",
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("report.json written")

# ============================================================
# VERIFICATION
# ============================================================
print("\n=== VERIFICATION ===")
# Verify mhw_mask.nc
ds_check = xr.open_dataset('output/mhw_mask.nc')
print(f"mhw_mask.nc: shape={ds_check.mhw.shape}, dtype={ds_check.mhw.dtype}")
print(f"  time: {ds_check.time.values[0]} to {ds_check.time.values[-1]}")
print(f"  lat: {ds_check.lat.values[0]} to {ds_check.lat.values[-1]}, n={len(ds_check.lat)}")
print(f"  lon: {ds_check.lon.values[0]} to {ds_check.lon.values[-1]}, n={len(ds_check.lon)}")
print(f"  mhw unique values: {np.unique(ds_check.mhw.values)}")
print(f"  mhw sum: {ds_check.mhw.values.sum()}")

# Verify report.json
with open('output/report.json', 'r') as f:
    report_check = json.load(f)
print(f"\nreport.json:")
print(f"  region: {report_check['region']}")
print(f"  baseline_analysed: {report_check['baseline_analysed']}")
print(f"  target_analysed: {report_check['target_analysed']}")
print(f"  events: {report_check['events']}")
print(f"  complete: {report_check['complete']}")
print(f"  caveats: '{report_check['caveats']}'")

print("\nAnalysis complete!")
