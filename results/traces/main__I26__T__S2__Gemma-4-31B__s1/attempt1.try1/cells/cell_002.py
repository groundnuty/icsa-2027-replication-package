import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
import os
from datetime import timedelta

# Configuration
region = {"lat_min": 57.83, "lat_max": 59.03, "lon_min": 17.41, "lon_max": 18.61}
target_start_str = "2007-06-01"
target_end_str = "2007-08-31"
baseline_start_str = "1992-01-01"
baseline_end_str = "2002-12-31"
file_path = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"

def get_doy_fixed(date):
    month_lengths = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_lengths[:date.month - 1]) + date.day

# 1. Load and slice data
fs = fsspec.filesystem('onedata')
with fs.open(file_path, "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")

# Variable name and coords
var_name = 'analysed_sst'
lat_name = 'latitude'
lon_name = 'longitude'

# Slice region first to reduce size
ds_region = ds.sel(
    latitude=slice(region["lat_min"], region["lat_max"]),
    longitude=slice(region["lon_min"], region["lon_max"])
)

# Time slices
# Baseline pool windows can extend from 1991-12-27 to 2003-01-05
ds_baseline_ext = ds_region.sel(time=slice("1991-12-27", "2003-01-05")).load()
ds_target = ds_region.sel(time=slice(target_start_str, target_end_str)).load()

sst_baseline_ext = ds_baseline_ext[var_name].astype(np.float64)
sst_target = ds_target[var_name].astype(np.float64)

# Coordinates for final mask
target_times = ds_target.time.values
target_lats = ds_target.latitude.values
target_lons = ds_target.longitude.values

# 2. Threshold and Climatology
# Setup indices
time_idx = sst_baseline_ext.time
baseline_dates = pd.to_datetime(time_idx.values)

# Find baseline dates that are actually within 1992-01-01 to 2002-12-31
baseline_mask = (baseline_dates >= pd.Timestamp(baseline_start_str)) & (baseline_dates <= pd.Timestamp(baseline_end_str))
baseline_core_dates = baseline_dates[baseline_mask]

# Precompute DOY for all dates in the extended baseline
all_baseline_doy = np.array([get_doy_fixed(t) for t in baseline_dates])

# Arrays for threshold and climatology: (lat, lon, doy)
# doy is 1-366, so we use index 0-365 (doy-1)
n_lat = len(target_lats)
n_lon = len(target_lons)
thresholds = np.full((n_lat, n_lon, 366), np.nan, dtype=np.float64)
climatologies = np.full((n_lat, n_lon, 366), np.nan, dtype=np.float64)

# Map of dates to their indices in sst_baseline_ext
date_to_idx = {date: i for i, date in enumerate(baseline_dates)}

for d in range(1, 367):
    if d == 60:
        continue
    
    # Find baseline dates with DOY == d
    # Use a loop over the baseline_core_dates
    pool_indices = []
    for t_base in baseline_core_dates:
        if get_doy_fixed(t_base) == d:
            # Window +/- 5 days
            for offset in range(-5, 6):
                t_window = t_base + timedelta(days=offset)
                if t_window in date_to_idx:
                    pool_indices.append(date_to_idx[t_window])
    
    if pool_indices:
        # Extract pool for all cells: (len(pool), lat, lon)
        pool_data = sst_baseline_ext.values[pool_indices, :, :]
        
        # Compute 90th percentile (Hazen) and mean across the first dimension (time)
        # numpy.quantile(..., method='hazen')
        thresholds[:, :, d-1] = np.nanquantile(pool_data, 0.9, axis=0, method='hazen')
        climatologies[:, :, d-1] = np.nanmean(pool_data, axis=0)

# Handle day 60: mean of 59 and 61
thresholds[:, :, 59] = (thresholds[:, :, 58] + thresholds[:, :, 60]) / 2
climatologies[:, :, 59] = (climatologies[:, :, 58] + climatologies[:, :, 60]) / 2

# Smoothing: 31-day centred moving mean (wraps around)
def smooth_366(arr):
    # arr: (lat, lon, 366)
    smoothed = np.zeros_like(arr)
    for d in range(366):
        # Days d-15 to d+15 (mod 366)
        indices = [(d + offset) % 366 for offset in range(-15, 16)]
        # Average across the 31 days
        smoothed[:, :, d] = np.nanmean(arr[:, :, indices], axis=-1)
    return smoothed

thresholds_smooth = smooth_366(thresholds)
climatologies_smooth = smooth_366(climatologies)

# 3. Per-cell MHWs
# target_sst: (time, lat, lon)
# thresholds_smooth: (lat, lon, 366)
target_sst_vals = sst_target.values
target_dates = pd.to_datetime(target_times)
target_doys = np.array([get_doy_fixed(t) for t in target_dates])

# hot_mask: (time, lat, lon)
hot_mask = np.zeros(target_sst_vals.shape, dtype=bool)

for t_idx, doy in enumerate(target_doys):
    # threshold for this day: (lat, lon)
    thresh_day = thresholds_smooth[:, :, doy-1]
    # SST for this day: (lat, lon)
    sst_day = target_sst_vals[t_idx, :, :]
    hot_mask[t_idx, :, :] = sst_day >= thresh_day

# Find and join MHWs for each cell
# mhw_mask: (time, lat, lon)
mhw_mask = np.zeros(target_sst_vals.shape, dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        cell_hot = hot_mask[:, i, j]
        cell_mhw = np.zeros(len(cell_hot), dtype=np.uint8)
        
        # Find runs of hot days
        # a run of at least 5 consecutive hot days
        # join gaps of 1 or 2 non-hot days
        
        # Identify all hot runs
        # Logic: 
        # 1. Find all contiguous blocks of hot days.
        # 2. If length >= 5, mark as MHW.
        # 3. Join MHWs if separated by 1 or 2 non-hot days.
        
        # Simpler: 
        # Step 1: Find runs >= 5.
        # Step 2: Repeatedly join any two MHW regions separated by <= 2 days.
        
        # Use a temporary array to mark initial MHWs
        temp_mhw = np.zeros(len(cell_hot), dtype=bool)
        
        # Find all runs
        start = None
        for t in range(len(cell_hot)):
            if cell_hot[t] and start is None:
                start = t
            elif not cell_hot[t] and start is not None:
                if t - start >= 5:
                    temp_mhw[start:t] = True
                start = None
        if start is not None and len(cell_hot) - start >= 5:
            temp_mhw[start:] = True
            
        # Join gaps of 1 or 2 days
        # Repeat joining until no more joins possible
        while True:
            changed = False
            # Find gaps of 1 or 2
            # a gap of 1: temp_mhw[t] == 0 and temp_mhw[t-1] == 1 and temp_mhw[t+1] == 1
            # a gap of 2: temp_mhw[t] == 0 and temp_mhw[t+1] == 0 and temp_mhw[t-1] == 1 and temp_mhw[t+2] == 1
            for t in range(1, len(temp_mhw) - 1):
                if not temp_mhw[t] and temp_mhw[t-1] and temp_mhw[t+1]:
                    temp_mhw[t] = True
                    changed = True
            for t in range(1, len(temp_mhw) - 2):
                if not temp_mhw[t] and not temp_mhw[t+1] and temp_mhw[t-1] and temp_mhw[t+2]:
                    temp_mhw[t] = True
                    temp_mhw[t+1] = True
                    changed = True
            if not changed:
                break
        
        cell_mhw[:] = temp_mhw.astype(np.uint8)
        mhw_mask[:, i, j] = cell_mhw

# 4. Regional Events
# active_days: (time)
active_days = np.any(mhw_mask == 1, axis=(1, 2))

regional_events = []
start = None
for t in range(len(active_days)):
    if active_days[t] and start is None:
        start = t
    elif not active_days[t] and start is not None:
        regional_events.append({
            "onset": target_dates[start].strftime("%Y-%m-%d"),
            "end": target_dates[t-1].strftime("%Y-%m-%d")
        })
        start = None
if start is not None:
    regional_events.append({
        "onset": target_dates[start].strftime("%Y-%m-%d"),
        "end": target_dates[-1].strftime("%Y-%m-%d")
    })

# Save output
os.makedirs("output", exist_ok=True)

# mhw_mask.nc
# Dimensions: time, lat, lon
# Time: target_times
# Lat: target_lats
# Lon: target_lons
mhw_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={"time": target_times, "latitude": target_lats, "longitude": target_lons}
)
mhw_ds.to_netcdf("output/mhw_mask.nc")

# report.json
report = {
    "region": region,
    "baseline_analysed": {
        "start": baseline_core_dates[0].strftime("%Y-%m-%d"),
        "end": baseline_core_dates[-1].strftime("%Y-%m-%d")
    },
    "target_analysed": {
        "start": target_dates[0].strftime("%Y-%m-%d"),
        "end": target_dates[-1].strftime("%Y-%m-%d")
    },
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Processing complete.")
