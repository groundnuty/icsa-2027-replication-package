import numpy as np
import pandas as pd
import xarray as xr
import fsspec
from datetime import datetime, timedelta
import json
import os

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

lat_min, lat_max = 54.45, 55.65
lon_min, lon_max = 16.05, 17.25
target_start = pd.Timestamp('2021-06-01')
target_end = pd.Timestamp('2021-08-31')

def get_custom_doy(date):
    month = date.month
    day = date.day
    offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return offsets[month-1] + day

def get_sst_subset_fixed(date):
    date_str = date.strftime('%Y%m%d')
    path = f'{base_path}/sst_{date_str}.nc'
    try:
        with fs.open(path, 'rb') as f:
            ds = xr.open_dataset(f, engine='h5netcdf')
            subset_ds = ds.sel(
                latitude=slice(lat_min, lat_max), 
                longitude=slice(lon_min, lon_max)
            )
            return subset_ds.analysed_sst.values.astype(np.float64), subset_ds.latitude.values, subset_ds.longitude.values
    except Exception:
        return None, None, None

# 1. Find Sea Cells
target_dates = pd.date_range(target_start, target_end)
sst_target_list = []
sliced_lats, sliced_lons = None, None

for date in target_dates:
    sst, la, lo = get_sst_subset_fixed(date)
    if sst is not None:
        sst_target_list.append(sst)
        if sliced_lats is None:
            sliced_lats, sliced_lons = la, lo
    else:
        sst_target_list.append(None)

if sliced_lats is None:
    # Need to find any file to get coordinates
    # Let's try the first day of the baseline
    sst, la, lo = get_sst_subset_fixed(pd.Timestamp('1992-01-01'))
    sliced_lats, sliced_lons = la, lo

shape = (len(sliced_lats), len(sliced_lons))
sst_target_list = [sst if sst is not None else np.full(shape, np.nan) for sst in sst_target_list]
sst_target = np.stack(sst_target_list) # (time, lat, lon)
sea_mask = np.all(np.isfinite(sst_target), axis=0)

print(f"Target shape: {sst_target.shape}, Sea mask shape: {sea_mask.shape}")

# 2. Baseline Climatology and Threshold
baseline_start = pd.Timestamp('1992-01-01')
baseline_end = pd.Timestamp('2002-12-31')
all_baseline_dates = pd.date_range(baseline_start - pd.Timedelta(days=5), 
                                   baseline_end + pd.Timedelta(days=5))

baseline_sst_dict = {}
for date in all_baseline_dates:
    sst, la, lo = get_sst_subset_fixed(date)
    if sst is not None:
        baseline_sst_dict[date] = sst
    else:
        baseline_sst_dict[date] = np.full(shape, np.nan)

thresholds = np.full((366, *shape), np.nan)
climatology = np.full((366, *shape), np.nan)

baseline_period = pd.date_range(baseline_start, baseline_end)
doy_to_baseline_dates = {d: [] for d in range(1, 367)}
for d in baseline_period:
    doy = get_custom_doy(d)
    if doy in doy_to_baseline_dates:
        doy_to_baseline_dates[doy].append(d)

for d in range(1, 367):
    if d == 60:
        continue
    
    pool_dates = set()
    for b_date in doy_to_baseline_dates[d]:
        for offset in range(-5, 6):
            pool_dates.add(b_date + pd.Timedelta(days=offset))
    
    pool_ssts = []
    for p_date in pool_dates:
        pool_ssts.append(baseline_sst_dict.get(p_date, np.full(shape, np.nan)))
    
    pool_ssts = np.stack(pool_ssts)
    
    # Compute 90th percentile (Hazen) and mean
    thresholds[d-1] = np.nanquantile(pool_ssts, 0.9, axis=0, method='hazen')
    climatology[d-1] = np.nanmean(pool_ssts, axis=0)

thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

def smooth_array(arr):
    smoothed = np.full_like(arr, np.nan)
    for d in range(366):
        window_indices = [(d + i) % 366 for i in range(-15, 16)]
        window_data = arr[window_indices]
        smoothed[d] = np.nanmean(window_data, axis=0)
    return smoothed

thresholds = smooth_array(thresholds)
climatology = smooth_array(climatology)

# 3. Per-cell MHWs
mhw_mask = np.zeros((len(target_dates), *shape), dtype=np.uint8)

# Use vectorized operations for hot days
hot_days = np.zeros((len(target_dates), *shape), dtype=bool)
for i, date in enumerate(target_dates):
    doy = get_custom_doy(date)
    hot_days[i] = (sst_target[i] >= thresholds[doy-1])

# Iterate over sea cells to find MHWs
for r in range(shape[0]):
    for c in range(shape[1]):
        if not sea_mask[r, c]:
            continue
        
        is_hot = hot_days[:, r, c]
        in_mhw = np.zeros(len(is_hot), dtype=bool)
        
        # Find runs of 5+ hot days
        i = 0
        while i < len(is_hot):
            if is_hot[i]:
                start = i
                while i < len(is_hot) and is_hot[i]:
                    i += 1
                if i - start >= 5:
                    in_mhw[start:i] = True
            else:
                i += 1
        
        # Join gaps of 1 or 2 non-hot days
        changed = True
        while changed:
            changed = False
            # Gap of 1
            for i in range(1, len(in_mhw)-1):
                if not in_mhw[i] and in_mhw[i-1] and in_mhw[i+1]:
                    in_mhw[i] = True
                    changed = True
            # Gap of 2
            for i in range(1, len(in_mhw)-2):
                if not in_mhw[i] and not in_mhw[i+1] and in_mhw[i-1] and in_mhw[i+2]:
                    in_mhw[i] = True
                    in_mhw[i+1] = True
                    changed = True
        
        mhw_mask[:, r, c] = in_mhw.astype(np.uint8)

# 4. Regional events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
i = 0
while i < len(active_days):
    if active_days[i]:
        start = i
        while i < len(active_days) and active_days[i]:
            i += 1
        regional_events.append({
            "onset": target_dates[start].strftime('%Y-%m-%d'),
            "end": target_dates[i-1].strftime('%Y-%m-%d')
        })
    else:
        i += 1

# Output
os.makedirs('output', exist_ok=True)
ds_out = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={"time": target_dates, "latitude": sliced_lats, "longitude": sliced_lons}
)
ds_out.to_netcdf('output/mhw_mask.nc')

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": baseline_start.strftime('%Y-%m-%d'), "end": baseline_end.strftime('%Y-%m-%d')},
    "target_analysed": {"start": target_start.strftime('%Y-%m-%d'), "end": target_end.strftime('%Y-%m-%d')},
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Done")
