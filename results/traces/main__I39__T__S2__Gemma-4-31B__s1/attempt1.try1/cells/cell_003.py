import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
from datetime import datetime, timedelta

def get_doy(dt):
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

with fs.open(file_path, "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")
    ds_region = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))
    sst_target = ds_region.sel(time=slice(target_start, target_end)).analysed_sst.load().astype(np.float64)
    sst_baseline = ds_region.sel(time=slice(baseline_data_start, baseline_data_end)).analysed_sst.load().astype(np.float64)

# Sea cells: SST finite on every day of target period
# sst_target is (time, lat, lon)
# finite = ~np.isnan(sst_target) & ~np.isinf(sst_target)
finite_mask = np.all(np.isfinite(sst_target), axis=0)
sea_cells = finite_mask # (lat, lon)

# Baseline dates and their DOYs
baseline_dates = pd.date_range(baseline_start_date, baseline_end_date)
baseline_data_times = pd.to_datetime(sst_baseline.time.values)

# Precompute DOYs for baseline data
baseline_data_doys = np.array([get_doy(t.to_pydatetime()) for t in baseline_data_times])

# For each d in 1..366, d != 60
thresholds = np.full((366, sst_target.latitude.size, sst_target.longitude.size), np.nan)
climatology = np.full((366, sst_target.latitude.size, sst_target.longitude.size), np.nan)

# To speed up, we can iterate over d and find the indices in sst_baseline
for d in range(1, 367):
    if d == 60:
        continue
    
    # Dates in baseline_dates (1992-2002) with DOY == d
    dates_with_d = [dt for dt in baseline_dates if get_doy(dt.to_pydatetime()) == d]
    
    # Union of windows [dt-5, dt+5]
    window_dates = set()
    for dt in dates_with_d:
        for offset in range(-5, 6):
            window_dates.add(dt + pd.Timedelta(days=offset))
    
    # Find indices of these window_dates in sst_baseline.time
    # Since sst_baseline.time is sorted, we can find indices efficiently
    window_dates_sorted = sorted(list(window_dates))
    
    # Map window_dates to indices in sst_baseline
    indices = []
    # Create a map for fast lookup
    time_map = {t: i for i, t in enumerate(baseline_data_times)}
    for wd in window_dates_sorted:
        if wd in time_map:
            indices.append(time_map[wd])
    
    if not indices:
        continue
    
    # Extract pool for all cells: (len(indices), lat, lon)
    pool = sst_baseline.values[indices, :, :]
    
    # Compute quantile (hazen) and mean for each cell
    # numpy.nanpercentile with method='hazen' matches MATLAB's quantile
    # Note: np.nanpercentile is slower. Let's use np.nanmean and a manual hazen for quantile if needed, 
    # but let's try nanpercentile first.
    thresholds[d-1] = np.nanpercentile(pool, 90, axis=0, method='hazen')
    climatology[d-1] = np.nanmean(pool, axis=0)

# Fill day 60
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

# Smooth with 31-day moving mean (wrap around)
def smooth(arr):
    # arr is (366, lat, lon)
    smoothed = np.zeros_like(arr)
    for d in range(366):
        # window is d-15 to d+15
        indices = [(d + i) % 366 for i in range(-15, 16)]
        window = arr[indices, :, :]
        smoothed[d] = np.nanmean(window, axis=0)
    return smoothed

thresholds = smooth(thresholds)
climatology = smooth(climatology)

# Per-cell MHWs
# target_sst: (time, lat, lon), thresholds: (366, lat, lon)
target_times = pd.to_datetime(sst_target.time.values)
target_doys = np.array([get_doy(t.to_pydatetime()) for t in target_times])

# hot_days: (time, lat, lon)
hot_days = np.zeros(sst_target.shape, dtype=bool)
for t_idx, doy in enumerate(target_doys):
    # doy is 1-366, index is doy-1
    hot_days[t_idx] = sst_target[t_idx] >= thresholds[doy-1]

# Identify MHWs per cell
mhw_mask = np.zeros(sst_target.shape, dtype=np.uint8)

for lat_idx in range(sst_target.latitude.size):
    for lon_idx in range(sst_target.longitude.size):
        if not sea_cells[lat_idx, lon_idx]:
            continue
        
        cell_hot = hot_days[:, lat_idx, lon_idx]
        # Find runs of >= 5 hot days
        # Join gaps of 1 or 2 non-hot days
        
        # A simple way to implement the gap joining:
        # First, identify initial hot runs.
        # Then, while there's a gap of 1-2 days between hot runs, join them.
        
        # Alternative: 
        # 1. Identify all hot runs of length >= 5.
        # 2. Merge any two runs separated by 1 or 2 days.
        # 3. Repeat merging until no more merges possible.
        
        # Let's use a more robust approach:
        # Create a binary mask of hot days.
        # A day is part of an MHW if it's part of a run of >= 5 hot days, 
        # OR if it's a gap day (1-2 days) between such runs.
        
        # Correct approach from MHW literature:
        # 1. Find all runs of >= 5 hot days.
        # 2. Join runs separated by <= 2 non-hot days.
        
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
            
        # Merge runs
        merged = False
        while not merged:
            merged = True
            new_runs = []
            i = 0
            while i < len(runs):
                if i < len(runs) - 1 and runs[i+1][0] - runs[i][1] <= 3: # gap of 1 or 2 days means diff is 2 or 3
                    # Join them
                    new_runs.append([runs[i][0], runs[i+1][1]])
                    i += 2
                    merged = False
                else:
                    new_runs.append(runs[i])
                    i += 1
            runs = new_runs
            if merged: # No merges in this pass
                break
        
        for start, end in runs:
            mhw_mask[start:end+1, lat_idx, lon_idx] = 1

# Regional events
# day is active if any cell is in MHW
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
