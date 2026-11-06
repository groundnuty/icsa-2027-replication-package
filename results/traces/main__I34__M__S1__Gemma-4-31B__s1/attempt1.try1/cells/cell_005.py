import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import json

# Parameters
lat_min, lat_max = 59.93, 61.13
lon_min, lon_max = 18.69, 19.89
target_start = pd.to_datetime('2007-06-01')
target_end = pd.to_datetime('2007-08-31')
baseline_start = pd.to_datetime('1992-01-01')
baseline_end = pd.to_datetime('2002-12-31')
dataset_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

def get_doy(date):
    # 1 Jan = 1, ..., 31 Dec = 366 (in leap years)
    # pandas .dayofyear is 1-indexed.
    return date.dayofyear

def load_region_sst(start_date, end_date):
    dates = pd.date_range(start_date, end_date)
    sst_list = []
    valid_dates = []
    lat_vals, lon_vals = None, None
    
    for date in dates:
        filename = f"sst_{date.strftime('%Y%m%d')}.nc"
        path = os.path.join(dataset_dir, filename)
        if os.path.exists(path):
            with xr.open_dataset(path, engine="h5netcdf") as ds:
                region_ds = ds.sel(
                    latitude=slice(lat_min, lat_max),
                    longitude=slice(lon_min, lon_max)
                )
                if lat_vals is None:
                    lat_vals = region_ds.latitude.values
                    lon_vals = region_ds.longitude.values
                sst_list.append(region_ds.analysed_sst.values.squeeze())
                valid_dates.append(date)
    
    if not sst_list:
        return None, None, None, None
    
    return np.array(sst_list, dtype=np.float64), valid_dates, lat_vals, lon_vals

# 1. Load Data
print("Loading baseline data...")
# Baseline pool extends +/- 5 days
sst_baseline, dates_baseline, lat_vals, lon_vals = load_region_sst(baseline_start - timedelta(days=5), baseline_end + timedelta(days=5))
print("Loading target data...")
sst_target, dates_target, _, _ = load_region_sst(target_start, target_end)

# target_dates_full: all dates in the target period
target_dates_full = pd.date_range(target_start, target_end)
# We need SST for every day of the target period for the "sea cells" definition.
# If some files are missing, we treat them as NaN.
sst_target_full = np.full((len(target_dates_full), len(lat_vals), len(lon_vals)), np.nan)
for i, date in enumerate(dates_target):
    # Find index in target_dates_full
    idx = (date - target_start).days
    if 0 <= idx < len(target_dates_full):
        sst_target_full[idx] = sst_baseline[0] # Wait, this is wrong. 
        # I'll redo the target loading to be exact.

# Let's fix target loading
def load_target_full():
    dates = pd.date_range(target_start, target_end)
    sst_full = []
    for date in dates:
        filename = f"sst_{date.strftime('%Y%m%d')}.nc"
        path = os.path.join(dataset_dir, filename)
        if os.path.exists(path):
            with xr.open_dataset(path, engine="h5netcdf") as ds:
                region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
                sst_full.append(region_ds.analysed_sst.values.squeeze())
        else:
            # Create NaN array if file is missing
            # Use first file to get shape
            if len(sst_full) > 0:
                sst_full.append(np.full(sst_full[0].shape, np.nan))
            else:
                # We need a shape. Let's find ANY file.
                sample_file = os.path.join(dataset_dir, 'sst_20231231.nc')
                with xr.open_dataset(sample_file, engine="h5netcdf") as ds:
                    region_ds = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
                    sst_full.append(np.full(region_ds.analysed_sst.values.squeeze().shape, np.nan))
    return np.array(sst_full, dtype=np.float64)

sst_target_full = load_target_full()
print("Target data loaded.")

# 1. Sea cells: finite SST on every day of the target period
# sst_target_full shape: (time, lat, lon)
sea_mask = np.all(np.isfinite(sst_target_full), axis=0)
print(f"Sea cells: {np.sum(sea_mask)} / {sea_mask.size}")

# 2. Threshold and climatology
# baseline dates: 1992-01-01 to 2002-12-31
baseline_dates_full = pd.date_range(baseline_start, baseline_end)

# Map baseline data to their dates
# sst_baseline is loaded from baseline_start-5 to baseline_end+5
# We need to align them.
baseline_sst_dict = {}
for date, sst in zip(dates_baseline, sst_baseline):
    baseline_sst_dict[date] = sst

thresholds = np.full((366, len(lat_vals), len(lon_vals)), np.nan)
climatologies = np.full((366, len(lat_vals), len(lon_vals)), np.nan)

# Process DOY 1 to 366 (excluding 60)
for d in range(1, 367):
    if d == 60:
        continue
    
    # Pool: SST values within +/- 5 days of any baseline date with DOY d
    pool_sst = []
    for b_date in baseline_dates_full:
        if b_date.dayofyear == d:
            # Window: b_date - 5 to b_date + 5
            for offset in range(-5, 6):
                window_date = b_date + timedelta(days=offset)
                if window_date in baseline_sst_dict:
                    pool_sst.append(baseline_sst_dict[window_date])
    
    if pool_sst:
        pool_sst = np.array(pool_sst) # (N, lat, lon)
        # Threshold: 90th percentile (Hazen)
        # numpy.quantile with method="hazen"
        thresholds[d-1] = np.nanquantile(pool_sst, 0.9, axis=0, method="hazen")
        # Climatology: mean
        climatologies[d-1] = np.nanmean(pool_sst, axis=0)

# Day 60: Mean of 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

# Smoothing: 31-day moving mean, wrap around
def smooth_366(arr):
    # arr shape: (366, lat, lon)
    smoothed = np.zeros_like(arr)
    for d in range(366):
        # Day d averages d-15 ... d+15 (modulo 366)
        # d is 0-indexed here, so d=0 is Jan 1
        window = []
        for offset in range(-15, 16):
            window.append(arr[(d + offset) % 366])
        smoothed[d] = np.nanmean(np.array(window), axis=0)
    return smoothed

thresholds_smoothed = smooth_366(thresholds)
climatologies_smoothed = smooth_366(climatologies)

# 3. Per-cell MHWs
# Target period: 2007-06-01 to 2007-08-31
# target_dates_full is the time axis
mhw_mask = np.zeros_like(sst_target_full, dtype=np.uint8)

for lat_idx in range(len(lat_vals)):
    for lon_idx in range(len(lon_vals)):
        if not sea_mask[lat_idx, lon_idx]:
            continue
        
        # Get SST for this cell over the target period
        cell_sst = sst_target_full[:, lat_idx, lon_idx]
        # Get thresholds for these days
        cell_thresholds = []
        for date in target_dates_full:
            doy = date.dayofyear
            cell_thresholds.append(thresholds_smoothed[doy-1, lat_idx, lon_idx])
        cell_thresholds = np.array(cell_thresholds)
        
        # Hot days
        hot = cell_sst >= cell_thresholds
        
        # Find runs of 5+ hot days
        # Joining gaps of 1-2 non-hot days
        # This is effectively: a day is MHW if it's part of a 5+ hot run,
        # or if it's a gap of 1-2 days between two MHW runs.
        
        # Correct way to join: 
        # 1. Identify all runs of hot days.
        # 2. Mark runs >= 5 as MHW.
        # 3. Join MHW runs separated by 1 or 2 non-hot days.
        
        is_mhw = np.zeros(len(hot), dtype=bool)
        # Find initial runs
        i = 0
        while i < len(hot):
            if hot[i]:
                start = i
                while i < len(hot) and hot[i]:
                    i += 1
                if (i - start) >= 5:
                    is_mhw[start:i] = True
            else:
                i += 1
        
        # Join gaps
        changed = True
        while changed:
            changed = False
            # Find gaps of 1 or 2 non-hot days between MHW segments
            # This can be done by iterating and checking
            for i in range(1, len(is_mhw)-1):
                if not is_mhw[i]:
                    # Gap of 1
                    if is_mhw[i-1] and is_mhw[i+1]:
                        is_mhw[i] = True
                        changed = True
                    # Gap of 2
                    elif i < len(is_mhw)-2 and is_mhw[i-1] and not is_mhw[i+1] and is_mhw[i+2]:
                        is_mhw[i] = True
                        is_mhw[i+1] = True
                        changed = True
                    elif i > 0 and not is_mhw[i-1] and is_mhw[i-2] and is_mhw[i+1]:
                        is_mhw[i-1] = True
                        is_mhw[i] = True
                        changed = True
        
        mhw_mask[:, lat_idx, lon_idx] = is_mhw.astype(np.uint8)

# 4. Regional events
# a day is active if at least one sea cell is inside a per-cell MHW
active_days = np.any(mhw_mask == 1, axis=(1, 2))

events = []
i = 0
while i < len(active_days):
    if active_days[i]:
        start_idx = i
        while i < len(active_days) and active_days[i]:
            i += 1
        events.append({
            "onset": target_dates_full[start_idx].strftime('%Y-%m-%d'),
            "end": target_dates_full[i-1].strftime('%Y-%m-%d')
        })
    else:
        i += 1

# Save output/mhw_mask.nc
# Create xarray dataset
ds_mhw = xr.Dataset(
    {"mhw": (["time", "latitude", "longitude"], mhw_mask)},
    coords={"time": target_dates_full, "latitude": lat_vals, "longitude": lon_vals}
)
os.makedirs('output', exist_ok=True)
ds_mhw.to_netcdf('output/mhw_mask.nc')

# Save output/report.json
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": baseline_start.strftime('%Y-%m-%d'), "end": baseline_end.strftime('%Y-%m-%d')},
    "target_analysed": {"start": target_start.strftime('%Y-%m-%d'), "end": target_end.strftime('%Y-%m-%d')},
    "events": events,
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Process complete.")
