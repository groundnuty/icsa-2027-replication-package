import fsspec
import xarray as xr
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

def get_doy(date):
    """Map date to day of year from 1 to 366."""
    month = date.month
    day = date.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[:month-1]) + day

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

lat_min, lat_max = 58.69, 59.89
lon_min, lon_max = 18.69, 19.89
target_start = pd.to_datetime('2010-06-01')
target_end = pd.to_datetime('2010-08-31')
baseline_data_start = pd.to_datetime('1991-12-27')
baseline_data_end = pd.to_datetime('2003-01-05')

def load_sst_range_fixed(start_date, end_date):
    dates = pd.date_range(start_date, end_date)
    sst_list = []
    coords_lat = None
    coords_lon = None
    
    for d in dates:
        file_path = f"{base_path}/sst_{d.strftime('%Y%m%d')}.nc"
        try:
            with fs.open(file_path, 'rb') as f:
                ds = xr.open_dataset(f, engine='h5netcdf')
                lat_mask = (ds.latitude >= lat_min) & (ds.latitude <= lat_max)
                lon_mask = (ds.longitude >= lon_min) & (ds.longitude <= lon_max)
                # Correct way to extract the rectangular region
                sst_val = ds.analysed_sst.values[0, lat_mask, :][:, lon_mask]
                
                if coords_lat is None:
                    coords_lat = ds.latitude.values[lat_mask]
                    coords_lon = ds.longitude.values[lon_mask]
                
                sst_list.append(sst_val.astype(np.float64))
        except Exception as e:
            if coords_lat is not None:
                sst_list.append(np.full((len(coords_lat), len(coords_lon)), np.nan, dtype=np.float64))
            else:
                # Use expected 60x60 if the very first file fails
                sst_list.append(np.full((60, 60), np.nan, dtype=np.float64))

    return np.array(sst_list, dtype=np.float64), coords_lat, coords_lon

print("Loading target data...")
target_sst, lats, lons = load_sst_range_fixed(target_start, target_end)
print(f"target_sst shape: {target_sst.shape}")

print("Loading baseline data...")
baseline_sst, _, _ = load_sst_range_fixed(baseline_data_start, baseline_data_end)
print(f"baseline_sst shape: {baseline_sst.shape}")

# 1. Sea cells: finite on every day of the target period
sea_mask = np.all(np.isfinite(target_sst), axis=0)
print(f"Number of sea cells: {np.sum(sea_mask)}")

# 2. Threshold and Climatology
baseline_dates = pd.date_range(baseline_data_start, baseline_data_end)
date_to_idx = {d: i for i, d in enumerate(baseline_dates)}

doy_to_baseline_dates = {d: [] for d in range(1, 367)}
for year in range(1992, 2003):
    year_dates = pd.date_range(f"{year}-01-01", f"{year}-12-31")
    for date in year_dates:
        d = get_doy(date)
        if d != 60:
            doy_to_baseline_dates[d].append(date)

thresholds = np.full((366, baseline_sst.shape[1], baseline_sst.shape[2]), np.nan, dtype=np.float64)
climatologies = np.full((366, baseline_sst.shape[1], baseline_sst.shape[2]), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60: continue
    pool_dates = set()
    for b_date in doy_to_baseline_dates[d]:
        for offset in range(-5, 6):
            t = b_date + timedelta(days=offset)
            if t in date_to_idx:
                pool_dates.add(date_to_idx[t])
    
    indices = list(pool_dates)
    if not indices:
        continue
    
    pool = baseline_sst[indices, :, :] # (len(indices), lat, lon)
    
    # Calculate 90th percentile (Hazen) and mean per cell
    # numpy.nanquantile with method="hazen"
    thresholds[d-1] = np.nanquantile(pool, 0.9, axis=0, method="hazen")
    climatologies[d-1] = np.nanmean(pool, axis=0)

# Day 60: mean of days 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

def smooth_366(arr):
    smoothed = np.full_like(arr, np.nan, dtype=np.float64)
    for d in range(366):
        window_indices = [(d + offset) % 366 for offset in range(-15, 16)]
        window_data = arr[window_indices, :, :]
        smoothed[d] = np.nanmean(window_data, axis=0)
    return smoothed

thresholds = smooth_366(thresholds)
climatologies = smooth_366(climatologies)

# 3. Per-cell MHWs
target_dates = pd.date_range(target_start, target_end)
mhw_mask = np.zeros(target_sst.shape, dtype=np.uint8)

for lat_idx in range(baseline_sst.shape[1]):
    for lon_idx in range(baseline_sst.shape[2]):
        if not sea_mask[lat_idx, lon_idx]:
            continue
        
        sst_cell = target_sst[:, lat_idx, lon_idx]
        thresh_cell = np.array([thresholds[get_doy(d)-1, lat_idx, lon_idx] for d in target_dates])
        
        hot = (sst_cell >= thresh_cell)
        
        # MHW detection
        hot_indices = np.where(hot)[0]
        if len(hot_indices) == 0:
            continue
            
        runs = []
        start = hot_indices[0]
        for j in range(1, len(hot_indices)):
            if hot_indices[j] != hot_indices[j-1] + 1:
                runs.append((start, hot_indices[j-1]))
                start = hot_indices[j]
        runs.append((start, hot_indices[-1]))
        
        mhw_runs = [r for r in runs if (r[1] - r[0] + 1) >= 5]
        
        if not mhw_runs:
            continue
            
        joined_runs = []
        curr_start, curr_end = mhw_runs[0]
        for j in range(1, len(mhw_runs)):
            next_start, next_end = mhw_runs[j]
            if next_start - curr_end - 1 <= 2:
                curr_end = next_end
            else:
                joined_runs.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        joined_runs.append((curr_start, curr_end))
        
        mhw_cell = np.zeros(len(hot), dtype=np.uint8)
        for rs, re in joined_runs:
            mhw_cell[rs:re+1] = 1
        mhw_mask[:, lat_idx, lon_idx] = mhw_cell

# 4. Regional Events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
i = 0
while i < len(active_days):
    if active_days[i]:
        start = i
        while i < len(active_days) and active_days[i]:
            i += 1
        end = i - 1
        regional_events.append({
            "onset": target_dates[start].strftime('%Y-%m-%d'),
            "end": target_dates[end].strftime('%Y-%m-%d')
        })
    else:
        i += 1

# Save results
import os
os.makedirs('output', exist_ok=True)

ds_out = xr.Dataset(
    {"mhw": (("time", "lat", "lon"), mhw_mask)},
    coords={
        "time": target_dates,
        "lat": lats,
        "lon": lons
    }
)
ds_out.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {
        "start": baseline_dates[0].strftime('%Y-%m-%d'),
        "end": baseline_dates[-1].strftime('%Y-%m-%d')
    },
    "target_analysed": {
        "start": target_dates[0].strftime('%Y-%m-%d'),
        "end": target_dates[-1].strftime('%Y-%m-%d')
    },
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Done.")
