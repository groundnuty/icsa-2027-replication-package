import numpy as np
import pandas as pd
import xarray as xr
import os
import json
from datetime import datetime, timedelta

# Configuration
local_file = '/work/sst_s2.nc'
lat_min, lat_max = 62.25, 63.45
lon_min, lon_max = 18.73, 19.93
target_start = '2012-06-01'
target_end = '2012-08-31'
baseline_start_year = 1992
baseline_end_year = 2002

def get_day_of_year(dt):
    """Custom day of year mapping: 1 Jan = 1, ... 29 Feb = 60, ... 31 Dec = 366."""
    # dt is a pandas Timestamp or datetime
    # In a leap year, 29 Feb is the 60th day.
    # In a non-leap year, 28 Feb is the 59th day and 1 March is the 60th day of the year in standard terms.
    # But the prompt says: "Non-leap years have no day 60."
    # This implies we should use the 'leap-year-aware' day of year.
    # Let's use the day of year (1-366) where 29 Feb is always 60.
    
    # A simple way is to use the day of year and adjust if it's after Feb 28 in a non-leap year.
    doy = dt.timetuple().tm_yday
    is_leap = (dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0))
    if not is_leap and doy > 59:
        # For non-leap years, doy 60 is March 1st.
        # The prompt says: "Non-leap years have no day 60."
        # "1 March = 61"
        return doy + 1
    return doy

# Open dataset and subset
ds = xr.open_dataset(local_file, engine="h5netcdf")
ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
sst = ds_region.analysed_sst.astype(np.float64)
times = pd.to_datetime(ds_region.time.values)

# Define target range
target_mask = (times >= pd.to_datetime(target_start)) & (times <= pd.to_datetime(target_end))
target_times = times[target_mask]
sst_target = sst.sel(time=slice(target_start, target_end))

# 1. Sea cells: SST is finite on every day of the target period.
# sst_target is (time, lat, lon)
# finite check along time axis
is_sea = np.all(np.isfinite(sst_target.values), axis=0)
sea_lats, sea_lons = np.where(is_sea)

# 2. Threshold and climatology
# Baseline dates (1992-01-01 to 2002-12-31)
baseline_mask = (times >= pd.to_datetime(f"{baseline_start_year}-01-01")) & \
                (times <= pd.to_datetime(f"{baseline_end_year}-12-31"))
baseline_times = times[baseline_mask]

# Need all SST values in the range [1991-12-27, 2003-01-05] for pooling
pool_range_mask = (times >= pd.to_datetime('1991-12-27')) & \
                  (times <= pd.to_datetime('2003-01-05'))
pool_times = times[pool_range_mask]
sst_pool_all = sst.sel(time=slice('1991-12-27', '2003-01-05'))

# Precompute day of year for all dates in the baseline range and the pool range
# Mapping for baseline_times to find dates with day-of-year d
baseline_doy = np.array([get_day_of_year(t) for t in baseline_times])

# Prepare arrays for thresholds and climatology
# dimensions: (day_of_year, lat, lon)
# Using index 0..365 for doy 1..366
thresholds = np.full((366, sst_region_shape := sst_target.shape[1:], np.nan)
climatologies = np.full((366, *sst_region_shape), np.nan)
# Wait, sst_target.shape[1:] is (lat, lon)
# Correcting:
thresholds = np.full((366, *sst_target.shape[1:]), np.nan, dtype=np.float64)
climatologies = np.full((366, *sst_target.shape[1:]), np.nan, dtype=np.float64)

# To speed up, we iterate over d from 1 to 366 (excluding 60)
# and find the union of windows [B-5, B+5] for all baseline dates B with doy(B)=d.

# For efficiency, let's map each date in pool_times to its index in sst_pool_all
pool_time_to_idx = {t: i for i, t in enumerate(pool_times)}

for d in range(1, 367):
    if d == 60:
        continue
    
    # Dates in baseline period with doy == d
    baseline_dates_with_d = baseline_times[baseline_doy == d]
    
    # All dates in the pool that fall into any [B-5, B+5] window
    pool_dates_for_d = set()
    for B in baseline_dates_with_d:
        for delta in range(-5, 6):
            date_in_window = B + timedelta(days=delta)
            if date_in_window in pool_time_to_idx:
                pool_dates_for_d.add(pool_time_to_idx[date_in_window])
    
    if not pool_dates_for_d:
        continue
    
    # Extract SST values for these dates
    # shape: (num_dates, lat, lon)
    pool_sst = sst_pool_all.values[list(pool_dates_for_d), :, :]
    
    # Threshold: 90th percentile (hazen), Climatology: Mean
    # We can use np.nanpercentile and np.nanmean along the 0-axis
    # Note: numpy's method="hazen" is equivalent to Hyndman-Fan type 5
    thresholds[d-1] = np.nanpercentile(pool_sst, 90, axis=0, method="hazen")
    climatologies[d-1] = np.nanmean(pool_sst, axis=0)

# Day 60 is mean of 59 and 61
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

# Smoothing: 31-day moving mean, wrapped around
def smooth_array(arr):
    smoothed = np.full_like(arr, np.nan)
    for d in range(1, 367):
        # Days d-15 to d+15, modulo 366
        indices = []
        for k in range(-15, 16):
            idx = (d + k - 1) % 366
            indices.append(idx)
        
        # Extract these days
        window = arr[indices, :, :]
        smoothed[d-1] = np.nanmean(window, axis=0)
    return smoothed

thresholds = smooth_array(thresholds)
climatologies = smooth_array(climatologies)

# 3. Per-cell MHWs
# target_times day of year
target_doy = np.array([get_day_of_year(t) for t in target_times])
# SST values for target period: (time, lat, lon)
sst_vals = sst_target.values

#Hot days mask
# sst_vals: (time, lat, lon)
# thresholds: (doy, lat, lon)
# For each t, lat, lon: sst_vals[t, lat, lon] >= thresholds[target_doy[t]-1, lat, lon]
hot_mask = np.zeros(sst_vals.shape, dtype=bool)
for t in range(len(target_times)):
    d = target_doy[t]
    # Note: get_day_of_year can return 60.
    # thresholds has size 366, index 0..365.
    # if d is 60, thresholds[59] is the one.
    hot_mask[t] = sst_vals[t] >= thresholds[d-1]

# Per-cell MHW logic
# For each cell (lat, lon), find runs of hot days
mhw_mask = np.zeros(sst_vals.shape, dtype=np.uint8)
num_time = sst_vals.shape[0]
num_lat = sst_vals.shape[1]
num_lon = sst_vals.shape[2]

for lat in range(num_lat):
    for lon in range(num_lon):
        if not is_sea[lat, lon]:
            continue
        
        cell_hot = hot_mask[:, lat, lon]
        cell_mhw = np.zeros(num_time, dtype=bool)
        
        # Find runs of hot days
        # A run is a sequence of True values
        i = 0
        while i < num_time:
            if cell_hot[i]:
                start = i
                while i < num_time and cell_hot[i]:
                    i += 1
                end = i - 1
                if (end - start + 1) >= 5:
                    cell_mhw[start : end+1] = True
            else:
                i += 1
        
        # Join gaps of 1 or 2 non-hot days
        # We repeat this until no more changes occur
        changed = True
        while changed:
            changed = False
            # Look for gaps of 1 or 2
            for j in range(1, num_time - 1):
                # Gap of 1: cell_mhw[j-1] and cell_mhw[j+1] are True, and j is a hot day?
                # No, the rule says "separated by 1 or 2 non-hot days".
                # This usually means if we have two MHW runs separated by 1-2 days, 
                # and those days are "hot", they might be part of the same.
                # Wait, the prompt says: "per-cell MHWs separated by 1 or 2 non-hot days are joined into one"
                # This means if day j and day j+2 are in MHWs, and day j+1 is not hot, they are joined.
                # Let's be precise: if there are two MHW segments [s1, e1] and [s2, e2] 
                # where s2 - e1 - 1 is 1 or 2, then they are joined.
                pass
            
            # Let's use a simpler gap-filling approach:
            # Find all runs of True in cell_mhw.
            runs = []
            curr_start = None
            for j in range(num_time):
                if cell_mhw[j] and curr_start is None:
                    curr_start = j
                elif not cell_mhw[j] and curr_start is not None:
                    runs.append((curr_start, j-1))
                    curr_start = None
            if curr_start is not None:
                runs.append((curr_start, num_time-1))
            
            # Merge runs separated by 1 or 2 days
            merged_runs = []
            if runs:
                curr_s, curr_e = runs[0]
                for next_s, next_e in runs[1:]:
                    if next_s - curr_e - 1 <= 2:
                        curr_e = next_e
                    else:
                        merged_runs.append((curr_s, curr_e))
                        curr_s, curr_e = next_s, next_e
                merged_runs.append((curr_s, curr_e))
            
            # Update cell_mhw
            new_cell_mhw = np.zeros(num_time, dtype=bool)
            for s, e in merged_runs:
                new_cell_mhw[s : e+1] = True
            
            if not np.array_equal(new_cell_mhw, cell_mhw):
                cell_mhw = new_cell_mhw
                changed = True
            else:
                changed = False
        
        mhw_mask[:, lat, lon] = cell_mhw.astype(np.uint8)

# 4. Regional events
# A day is active if at least one sea cell is in an MHW
active_days = np.any(mhw_mask == 1, axis=(1, 2))

# Regional events are maximal runs of active days
events = []
i = 0
while i < num_time:
    if active_days[i]:
        start = i
        while i < num_time and active_days[i]:
            i += 1
        end = i - 1
        events.append({
            "onset": target_times[start].strftime('%Y-%m-%d'),
            "end": target_times[end].strftime('%Y-%m-%d')
        })
    else:
        i += 1

# Save results
os.makedirs('output', exist_ok=True)

# mhw_mask.nc
# Use xarray to create the netCDF file
mhw_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask.astype(np.uint8))},
    coords={
        "time": target_times,
        "latitude": ds_region.latitude.values,
        "longitude": ds_region.longitude.values,
    }
)
mhw_ds.to_netcdf('output/mhw_mask.nc')

# report.json
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {
        "start": pool_times[0].strftime('%Y-%m-%d'),
        "end": pool_times[-1].strftime('%Y-%m-%d')
    },
    "target_analysed": {
        "start": target_times[0].strftime('%Y-%m-%d'),
        "end": target_times[-1].strftime('%Y-%m-%d')
    },
    "events": events,
    "complete": True,
    "caveats": ""
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)

print("Analysis complete. Files written.")
