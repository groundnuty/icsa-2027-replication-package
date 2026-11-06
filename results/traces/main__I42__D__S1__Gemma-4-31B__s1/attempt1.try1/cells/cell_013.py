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
    doy = dt.timetuple().tm_yday
    is_leap = (dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0))
    if not is_leap and doy > 59:
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
is_sea = np.all(np.isfinite(sst_target.values), axis=0)

# 2. Threshold and climatology
baseline_mask = (times >= pd.to_datetime(f"{baseline_start_year}-01-01")) & \
                (times <= pd.to_datetime(f"{baseline_end_year}-12-31"))
baseline_times = times[baseline_mask]

pool_range_mask = (times >= pd.to_datetime('1991-12-27')) & \
                  (times <= pd.to_datetime('2003-01-05'))
pool_times = times[pool_range_mask]
sst_pool_all = sst.sel(time=slice('1991-12-27', '2003-01-05'))

baseline_doy = np.array([get_day_of_year(t) for t in baseline_times])
pool_time_to_idx = {t: i for i, t in enumerate(pool_times)}

# Correct initialization of thresholds and climatologies
shape_lat_lon = sst_target.shape[1:]
thresholds = np.full((366, *shape_lat_lon), np.nan, dtype=np.float64)
climatologies = np.full((366, *shape_lat_lon), np.nan, dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    
    baseline_dates_with_d = baseline_times[baseline_doy == d]
    pool_dates_for_d = set()
    for B in baseline_dates_with_d:
        for delta in range(-5, 6):
            date_in_window = B + timedelta(days=delta)
            if date_in_window in pool_time_to_idx:
                pool_dates_for_d.add(pool_time_to_idx[date_in_window])
    
    if not pool_dates_for_d:
        continue
    
    pool_sst = sst_pool_all.values[list(pool_dates_for_d), :, :]
    thresholds[d-1] = np.nanpercentile(pool_sst, 90, axis=0, method="hazen")
    climatologies[d-1] = np.nanmean(pool_sst, axis=0)

thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

def smooth_array(arr):
    smoothed = np.full_like(arr, np.nan)
    for d in range(1, 367):
        indices = [(d + k - 1) % 366 for k in range(-15, 16)]
        window = arr[indices, :, :]
        smoothed[d-1] = np.nanmean(window, axis=0)
    return smoothed

thresholds = smooth_array(thresholds)
climatologies = smooth_array(climatologies)

# 3. Per-cell MHWs
target_doy = np.array([get_day_of_year(t) for t in target_times])
sst_vals = sst_target.values
hot_mask = np.zeros(sst_vals.shape, dtype=bool)
for t in range(len(target_times)):
    d = target_doy[t]
    hot_mask[t] = sst_vals[t] >= thresholds[d-1]

mhw_mask = np.zeros(sst_vals.shape, dtype=np.uint8)
num_time, num_lat, num_lon = sst_vals.shape

for lat in range(num_lat):
    for lon in range(num_lon):
        if not is_sea[lat, lon]:
            continue
        
        cell_hot = hot_mask[:, lat, lon]
        cell_mhw = np.zeros(num_time, dtype=bool)
        
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
        
        changed = True
        while changed:
            changed = False
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
active_days = np.any(mhw_mask == 1, axis=(1, 2))
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
mhw_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask.astype(np.uint8))},
    coords={
        "time": target_times,
        "latitude": ds_region.latitude.values,
        "longitude": ds_region.longitude.values,
    }
)
mhw_ds.to_netcdf('output/mhw_mask.nc')

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
