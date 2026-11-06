import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
import os
from datetime import datetime, timedelta

def get_doy(dt):
    # Fixed DOY mapping as per requirements
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:dt.month-1]) + dt.day

fs = fsspec.filesystem('onedata')
file_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

lat_min, lat_max = 60.49, 61.69
lon_min, lon_max = 17.25, 18.45
target_start = '2010-06-01'
target_end = '2010-08-31'
baseline_start_date = pd.Timestamp('1992-01-01')
baseline_end_date = pd.Timestamp('2002-12-31')
baseline_data_start = '1991-12-27'
baseline_data_end = '2003-01-05'

os.makedirs('output', exist_ok=True)

with fs.open(file_path, "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")
    ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    sst_target = ds_region.sel(time=slice(target_start, target_end)).analysed_sst.load().astype(np.float64)
    sst_baseline = ds_region.sel(time=slice(baseline_data_start, baseline_data_end)).analysed_sst.load().astype(np.float64)

# Sea cells: SST finite on every day of target period
finite_mask = np.all(np.isfinite(sst_target), axis=0)
sea_cells = finite_mask # (lat, lon)

# Baseline dates and their DOYs
baseline_dates = pd.date_range(baseline_start_date, baseline_end_date)
baseline_data_times = pd.to_datetime(sst_baseline.time.values)
time_map = {t: i for i, t in enumerate(baseline_data_times)}

thresholds = np.full((366, sst_target.latitude.size, sst_target.longitude.size), np.nan)
climatology = np.full((366, sst_target.latitude.size, sst_target.longitude.size), np.nan)

for d in range(1, 367):
    if d == 60:
        continue
    
    dates_with_d = [dt for dt in baseline_dates if get_doy(dt.to_pydatetime()) == d]
    window_dates = set()
    for dt in dates_with_d:
        for offset in range(-5, 6):
            window_dates.add(dt + pd.Timedelta(days=offset))
    
    indices = [time_map[wd] for wd in window_dates if wd in time_map]
    
    if not indices:
        continue
    
    pool = sst_baseline.values[indices, :, :]
    thresholds[d-1] = np.nanpercentile(pool, 90, axis=0, method='hazen')
    climatology[d-1] = np.nanmean(pool, axis=0)

# Fill day 60
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

# Smooth with 31-day moving mean (wrap around)
def smooth(arr):
    smoothed = np.zeros_like(arr)
    for d in range(366):
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices, :, :]
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

thresholds = smooth(thresholds)
climatology = smooth(climatology)

# Per-cell MHWs
target_times = pd.to_datetime(sst_target.time.values)
target_doys = np.array([get_doy(t.to_pydatetime()) for t in target_times])

hot_days = np.zeros(sst_target.shape, dtype=bool)
for t_idx, doy in enumerate(target_doys):
    hot_days[t_idx] = sst_target[t_idx] >= thresholds[doy-1]

mhw_mask = np.zeros(sst_target.shape, dtype=np.uint8)

for lat_idx in range(sst_target.latitude.size):
    for lon_idx in range(sst_target.longitude.size):
        if not sea_cells[lat_idx, lon_idx]:
            continue
        
        cell_hot = hot_days[:, lat_idx, lon_idx]
        runs = []
        start = None
        for i in range(len(cell_hot)):
            if cell_hot[i]:
                if start is None:
                    start = i
            else:
                if start is not None:
                    if i - start >= 5:
                        runs.append([start, i - 1])
                    start = None
        if start is not None:
            if len(cell_hot) - start >= 5:
                runs.append([start, len(cell_hot) - 1])
        
        if not runs:
            continue
            
        # Merge runs separated by 1 or 2 non-hot days (s2 - e1 <= 3)
        while True:
            merged_any = False
            new_runs = []
            i = 0
            while i < len(runs):
                if i < len(runs) - 1 and runs[i+1][0] - runs[i][1] <= 3:
                    new_runs.append([runs[i][0], runs[i+1][1]])
                    i += 2
                    merged_any = True
                else:
                    new_runs.append(runs[i])
                    i += 1
            runs = new_runs
            if not merged_any:
                break
        
        for start, end in runs:
            mhw_mask[start:end+1, lat_idx, lon_idx] = 1

# Regional events
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
start = None
for i in range(len(active_days)):
    if active_days[i]:
        if start is None:
            start = i
    else:
        if start is not None:
            regional_events.append({"onset": target_times[start].strftime('%Y-%m-%d'), 
                                    "end": target_times[i-1].strftime('%Y-%m-%d')})
            start = None
if start is not None:
    regional_events.append({"onset": target_times[start].strftime('%Y-%m-%d'), 
                            "end": target_times[-1].strftime('%Y-%m-%d')})

# Save output
mhw_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={"time": target_times, "latitude": sst_target.latitude, "longitude": sst_target.longitude}
)
mhw_ds.to_netcdf("output/mhw_mask.nc")

report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": baseline_start_date.strftime('%Y-%m-%d'), "end": baseline_end_date.strftime('%Y-%m-%d')},
    "target_analysed": {"start": target_start, "end": target_end},
    "events": regional_events,
    "complete": True,
    "caveats": ""
}
with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Done.")
