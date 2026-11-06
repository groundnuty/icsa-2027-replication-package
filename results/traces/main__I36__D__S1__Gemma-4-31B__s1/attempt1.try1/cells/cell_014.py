import fsspec
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# Parameters
LAT_MIN, LAT_MAX = 60.09, 61.29
LON_MIN, LON_MAX = 20.01, 21.21
TARGET_START = "2003-06-01"
TARGET_END = "2003-08-31"
BASELINE_START = "1992-01-01"
BASELINE_END = "2002-12-31"

# Data path
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'

fs = fsspec.filesystem('onedata')
if not os.path.exists(local_path):
    fs.get(remote_path, local_path)

# Open dataset and slice region
ds = xr.open_dataset(local_path, engine="h5netcdf")
ds_region = ds.sel(
    latitude=slice(LAT_MIN, LAT_MAX),
    longitude=slice(LON_MIN, LON_MAX)
).compute()

sst = ds_region['analysed_sst'].astype(np.float64)
lat = ds_region.latitude.values
lon = ds_region.longitude.values
time_coords = pd.to_datetime(ds_region.time.values)

# 1. Sea cells: SST is finite on every day of the target period
time_target_start = np.datetime64(TARGET_START)
time_target_end = np.datetime64(TARGET_END)
target_mask = (ds_region.time.values >= time_target_start) & (ds_region.time.values <= time_target_end)
sst_target = sst.sel(time=target_mask)
is_sea = np.all(np.isfinite(sst_target.values), axis=0)

# 2. Threshold and climatology
time_baseline_start = np.datetime64(BASELINE_START)
time_baseline_end = np.datetime64(BASELINE_END)
pool_start = time_baseline_start - np.timedelta64(5, 'D')
pool_end = time_baseline_end + np.timedelta64(5, 'D')
sst_pool = sst.sel(time=slice(pool_start, pool_end))

pool_times = pd.to_datetime(sst_pool.time.values)
pool_vals = sst_pool.values # (time, lat, lon)
pool_dates_np = pool_times.values

baseline_dates = pd.date_range(BASELINE_START, BASELINE_END)
baseline_days_of_year = baseline_dates.day_of_year.values
baseline_dates_np = baseline_dates.values

thresholds = np.full((366, len(lat), len(lon)), np.nan)
climatology = np.full((366, len(lat), len(lon)), np.nan)

for d in range(1, 367):
    if d == 60:
        continue
    
    b_indices = np.where(baseline_days_of_year == d)[0]
    if len(b_indices) == 0:
        continue
    
    b_dates = baseline_dates_np[b_indices]
    mask_pool = np.zeros(len(pool_dates_np), dtype=bool)
    for b_date in b_dates:
        diff = np.abs(pool_dates_np - b_date)
        mask_pool |= (diff <= np.timedelta64(5, 'D'))
    
    pool_data = pool_vals[mask_pool, :, :]
    
    # Climatology
    climatology[d-1, :, :] = np.nanmean(pool_data, axis=0)
    
    # Threshold (90th percentile, method="hazen")
    # Using np.nanquantile with method="hazen"
    try:
        thresholds[d-1, :, :] = np.nanquantile(pool_data, 0.9, axis=0, method="hazen")
    except TypeError:
        # Fallback for older numpy: implement hazen manually
        # Hazen: (i-0.5)/n. For p=0.9, i = 0.9n + 0.5.
        # Since np.nanquantile isn't available with method="hazen", we loop
        for r in range(len(lat)):
            for c in range(len(lon)):
                vals = pool_data[:, r, c]
                filtered = np.sort(vals[~np.isnan(vals)])
                if len(filtered) > 0:
                    n = len(filtered)
                    # Hazen quantile: p = (i - 0.5) / n  => i = p*n + 0.5
                    idx = 0.9 * n + 0.5
                    # We need to interpolate if idx is not an integer
                    # But MATLAB's default quantile(X, 0.9) is essentially Type 7.
                    # HOWEVER, the prompt says: "MATLAB's quantile does by default, which is numpy's method="hazen"".
                    # Actually, MATLAB's default is Type 7.
                    # Let's check the prompt again: "the 90th percentile of the pool, computed as MATLAB's quantile does by default, which is numpy's method="hazen" (Hyndman–Fan type 5)".
                    # This is a direct instruction: use numpy's method="hazen".
                    # If numpy is too old, I must implement Hyndman-Fan Type 5.
                    # Type 5: i = p(n+1), then interpolate between floor(i) and ceil(i).
                    # Wait, Type 5 is actually: index = p(n+1).
                    # Let's use the standard formula for Type 5:
                    # q = x[i] if i is integer; else interpolate.
                    # Actually, let's just try to update numpy or use a reliable implementation.
                    # Let's use the manual interpolation for Type 5.
                    i = 0.9 * (n + 1)
                    if i <= 1:
                        thresholds[d-1, r, c] = filtered[0]
                    elif i >= n:
                        thresholds[d-1, r, c] = filtered[-1]
                    else:
                        low = int(np.floor(i)) - 1
                        high = int(np.ceil(i)) - 1
                        weight = i - np.floor(i)
                        thresholds[d-1, r, c] = (1 - weight) * filtered[low] + weight * filtered[high]

# Handle day 60
thresholds[59, :, :] = (thresholds[58, :, :] + thresholds[60, :, :]) / 2
climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2

# Smooth with 31-day moving mean (wrap around)
def smooth_366(arr):
    smoothed = np.full_like(arr, np.nan)
    for i in range(366):
        window = []
        for j in range(i - 15, i + 16):
            idx = j % 366
            window.append(arr[idx])
        smoothed[i] = np.nanmean(np.array(window), axis=0)
    return smoothed

thresholds_smooth = smooth_366(thresholds)
climatology_smooth = smooth_366(climatology)

# 3. Per-cell MHWs
# Only target period
target_dates = time_coords[target_mask]
sst_target_vals = sst_target.values
# Target day of year
target_doy = target_dates.day_of_year.values

# hot_mask: (time, lat, lon)
hot_mask = np.zeros(sst_target_vals.shape, dtype=bool)
for t_idx, doy in enumerate(target_doy):
    # doy is 1-366
    # Special case: doy 60 in target? 2003 is not a leap year.
    # target_doy for 2003: Feb 28 is 59, Mar 1 is 60.
    # Wait, "1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61".
    # This means in a non-leap year, Mar 1 is day 60?
    # Let's re-read: "Non-leap years have no day 60."
    # So for 2003, Mar 1 is day 60? No, "1 March = 61".
    # Let's check the provided mapping: "1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61".
    # This means in 2003, the day after 59 is 61.
    # Let's use a custom day-of-year function.
    pass

def custom_doy(dt):
    # 1 Jan = 1, ..., 28 Feb = 59, 29 Feb = 60, 1 Mar = 61...
    # This is exactly what dt.dayofyear does in leap years.
    # In non-leap years, dt.dayofyear for Mar 1 is 60.
    # But the instructions say "Non-leap years have no day 60" and "1 March = 61".
    # This means we should add 1 to the dayofyear if it's March 1st or later in a non-leap year.
    year = dt.year
    doy = dt.dayofyear
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    if not is_leap and doy >= 60:
        doy += 1
    return doy

target_doy_custom = np.array([custom_doy(d) for d in target_dates])

for t_idx, doy in enumerate(target_doy_custom):
    # doy is 1-366
    threshold = thresholds_smooth[doy-1, :, :]
    hot_mask[t_idx, :, :] = sst_target_vals[t_idx, :, :] >= threshold

# Identify runs of >= 5 days and join gaps
mhw_mask = np.zeros(hot_mask.shape, dtype=np.uint8)
for r in range(len(lat)):
    for c in range(len(lon)):
        if not is_sea[r, c]:
            continue
        
        cell_hot = hot_mask[:, r, c]
        cell_mhw = np.zeros(len(cell_hot), dtype=bool)
        
        # Find runs of 5+ hot days
        i = 0
        while i < len(cell_hot):
            if cell_hot[i]:
                start = i
                while i < len(cell_hot) and cell_hot[i]:
                    i += 1
                if i - start >= 5:
                    cell_mhw[start:i] = True
            else:
                i += 1
        
        # Join gaps of 1 or 2 non-hot days
        # Repeat until no more joins
        while True:
            changed = False
            i = 0
            while i < len(cell_hot) - 2:
                # If we have MHW, then 1-2 non-hot, then MHW
                # Gap of 1
                if not cell_mhw[i+1] and cell_mhw[i] and cell_mhw[i+2]:
                    cell_mhw[i+1] = True
                    changed = True
                # Gap of 2
                if i < len(cell_hot) - 3 and not cell_mhw[i+1] and not cell_mhw[i+2] and cell_mhw[i] and cell_mhw[i+3]:
                    cell_mhw[i+1] = True
                    cell_mhw[i+2] = True
                    changed = True
                i += 1
            if not changed:
                break
        mhw_mask[:, r, c] = cell_mhw.astype(np.uint8)

# 4. Regional events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
events = []
i = 0
while i < len(active_days):
    if active_days[i]:
        start_idx = i
        while i < len(active_days) and active_days[i]:
            i += 1
        events.append({
            "onset": target_dates[start_idx].strftime('%Y-%m-%d'),
            "end": target_dates[i-1].strftime('%Y-%m-%d')
        })
    else:
        i += 1

# Output files
os.makedirs('output', exist_ok=True)
# mhw_mask.nc
mhw_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={"time": target_dates, "latitude": lat, "longitude": lon}
)
mhw_ds.to_netcdf('output/mhw_mask.nc')

# report.json
report = {
    "region": {"lat_min": LAT_MIN, "lat_max": LAT_MAX, "lon_min": LON_MIN, "lon_max": LON_MAX},
    "baseline_analysed": {"start": BASELINE_START, "end": BASELINE_END},
    "target_analysed": {"start": TARGET_START, "end": TARGET_END},
    "events": events,
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Success")
