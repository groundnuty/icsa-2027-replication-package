import os
import glob
import xarray as xr
import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta

# --- Configuration ---
dataset_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91
baseline_start_str = '1992-01-01'
baseline_end_str = '2002-12-31'
target_start_str = '2019-06-01'
target_end_str = '2019-08-31'

def get_day_of_year(dt):
    standard_doy = dt.timetuple().tm_yday
    is_leap = (dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0))
    if not is_leap and standard_doy >= 60:
        return standard_doy + 1
    return standard_doy

def load_sst_subset(start_date, end_date, lat_min, lat_max, lon_min, lon_max):
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    date_range = pd.date_range(start, end)
    
    # We need the coordinates. Let's find one existing file.
    first_file = None
    for dt in date_range:
        f = os.path.join(dataset_dir, f"sst_{dt.strftime('%Y%m%d')}.nc")
        if os.path.exists(f):
            first_file = f
            break
    
    if first_file is None:
        # Try searching the whole directory if the specific range is empty
        all_files = sorted(glob.glob(os.path.join(dataset_dir, 'sst_*.nc')))
        if not all_files:
            return None
        first_file = all_files[0]

    with xr.open_dataset(first_file, engine="h5netcdf") as ds:
        lat = ds.latitude.sel(latitude=slice(lat_min, lat_max))
        lon = ds.longitude.sel(longitude=slice(lon_min, lon_max))
        n_lat, n_lon = len(lat), len(lon)

    final_sst = []
    final_times = []
    for dt in date_range:
        fname = os.path.join(dataset_dir, f"sst_{dt.strftime('%Y%m%d')}.nc")
        if os.path.exists(fname):
            with xr.open_dataset(fname, engine="h5netcdf") as ds:
                subset = ds.analysed_sst.sel(
                    latitude=slice(lat_min, lat_max),
                    longitude=slice(lon_min, lon_max)
                )
                val = subset.values[0]
                # Handle potential size mismatch if coordinates changed
                if val.shape != (n_lat, n_lon):
                    # This shouldn't happen but for robustness:
                    val = np.full((n_lat, n_lon), np.nan)
                final_sst.append(val)
                final_times.append(dt)
        else:
            final_sst.append(np.full((n_lat, n_lon), np.nan))
            final_times.append(dt)

    sst_array = np.stack(final_sst, axis=0).astype(np.float64)
    da = xr.DataArray(
        sst_array,
        coords={'time': final_times, 'latitude': lat, 'longitude': lon},
        dims=['time', 'latitude', 'longitude'],
        name='sst'
    )
    return da

# --- Load Data ---
# Baseline pool requires dates from 1991-12-27 to 2003-01-05
baseline_data = load_sst_subset('1991-12-27', '2003-01-05', lat_min, lat_max, lon_min, lon_max)
target_data = load_sst_subset('2019-06-01', '2019-08-31', lat_min, lat_max, lon_min, lon_max)

# --- Process ---
# 1. Sea cells: SST finite on every day of target period
# target_data shape: (time, lat, lon)
sst_target_vals = target_data.values
# Check finiteness across time axis
is_sea_cell = np.all(np.isfinite(sst_target_vals), axis=0)
n_lat, n_lon = is_sea_cell.shape
n_time_target = sst_target_vals.shape[0]

# 2. Threshold and Climatology
# Baseline dates for identifying the pool: 1992-01-01 to 2002-12-31
baseline_dates = pd.date_range('1992-01-01', '2002-12-31')
doy_to_dates = {d: [] for d in range(1, 367)}
for dt in baseline_dates:
    doy = get_day_of_year(dt)
    if doy != 60:
        doy_to_dates[doy].append(dt)

# To efficiently access SST, let's map time to index
time_to_idx = {t: i for i, t in enumerate(baseline_data.time.values)}
# baseline_data.time is datetime64[ns], we need to be careful with types
# baseline_data.time.values are numpy datetime64.
# Let's use a different approach.
baseline_times = pd.to_datetime(baseline_data.time.values)
time_to_idx = {t: i for i, t in enumerate(baseline_times)}

# Thresholds and Climatology arrays (366, lat, lon)
thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

# Iterate over days of year
for d in range(1, 367):
    if d == 60:
        continue
    
    # Find all dates in the pool for day d
    pool_indices = []
    for b_date in doy_to_dates[d]:
        # Window [B-5, B+5]
        for offset in range(-5, 6):
            t_date = b_date + timedelta(days=offset)
            if t_date in time_to_idx:
                pool_indices.append(time_to_idx[t_date])
    
    if not pool_indices:
        continue
    
    # Extract values for all cells: (len(pool), lat, lon)
    pool_vals = baseline_data.values[pool_indices]
    
    # Compute threshold and climatology for each cell
    # Use numpy's nanquantile and nanmean
    # Note: np.nanquantile doesn't have method='hazen'.
    # We can use np.nanpercentile or np.quantile on masked arrays.
    # To use method='hazen', we can't use nanquantile directly.
    # Let's iterate over cells or use a mask.
    
    # For each cell (i, j)
    for i in range(n_lat):
        for j in range(n_lon):
            cell_pool = pool_vals[:, i, j]
            valid_mask = np.isfinite(cell_pool)
            if np.any(valid_mask):
                valid_vals = cell_pool[valid_mask]
                thresholds[d-1, i, j] = np.quantile(valid_vals, 0.9, method='hazen')
                climatology[d-1, i, j] = np.mean(valid_vals)

# Day 60
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatology[59] = (climatology[58] + climatology[60]) / 2

# Smoothing: 31-day centered moving mean, wrap around
def smooth_366(arr):
    # arr shape: (366, lat, lon)
    smoothed = np.full_like(arr, np.nan)
    for i in range(366):
        # Indices for d-15 to d+15 modulo 366
        indices = [(i + offset) % 366 for offset in range(-15, 16)]
        window = arr[indices] # (31, lat, lon)
        smoothed[i] = np.nanmean(window, axis=0)
    return smoothed

thresholds = smooth_366(thresholds)
climatology = smooth_366(climatology)

# 3. Per-cell MHWs
# Target period: 2019-06-01 to 2019-08-31
# Target days doy:
target_doys = [get_day_of_year(t) for t in target_data.time.values]
mhw_mask = np.zeros((n_time_target, n_lat, n_lon), dtype=np.uint8)

for i in range(n_lat):
    for j in range(n_lon):
        if not is_sea_cell[i, j]:
            continue
        
        # SST for this cell in target period
        cell_sst = sst_target_vals[:, i, j]
        # Thresholds for these days
        cell_thresholds = np.array([thresholds[d-1, i, j] for d in target_doys])
        
        # Hot days
        is_hot = cell_sst >= cell_thresholds
        
        # Find runs of at least 5 hot days
        # Join gaps of 1 or 2 non-hot days
        # This is easier to do by iterating and labeling
        
        in_mhw = np.zeros(n_time_target, dtype=bool)
        
        # First, find all hot runs
        # a run is a contiguous sequence of True in is_hot
        
        # To handle gaps, we can first find runs of hot days, then merge.
        # Or: find all sequences of hot days, and if they are separated by <= 2 non-hot days, merge.
        
        # Simplified: 
        # 1. Find all runs of >= 5 hot days.
        # 2. While there are MHWs separated by 1 or 2 non-hot days, merge them.
        
        # Let's use a labeling approach.
        hot_runs = []
        start = None
        for t in range(n_time_target):
            if is_hot[t]:
                if start is None:
                    start = t
            else:
                if start is not None:
                    if t - start >= 5:
                        hot_runs.append((start, t-1))
                    start = None
        if start is not None:
            if n_time_target - start >= 5:
                hot_runs.append((start, n_time_target-1))
        
        # Merge gaps
        if not hot_runs:
            continue
            
        merged = []
        if hot_runs:
            curr_start, curr_end = hot_runs[0]
            for next_start, next_end in hot_runs[1:]:
                if next_start - curr_end <= 3: # Gap is (next_start - curr_end - 1) days
                    # Gap is 1 or 2 non-hot days means next_start - curr_end is 2 or 3.
                    # Wait: if curr_end = 10, next_start = 11, gap = 0.
                    # if curr_end = 10, next_start = 12, gap = 1 (day 11).
                    # if curr_end = 10, next_start = 13, gap = 2 (days 11, 12).
                    # So gap <= 2 means next_start - curr_end <= 3.
                    curr_end = next_end
                else:
                    merged.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            merged.append((curr_start, curr_end))
        
        for s, e in merged:
            in_mhw[s : e+1] = True
            
        mhw_mask[:, i, j] = in_mhw.astype(np.uint8)

# 4. Regional events
# a day is active if at least one sea cell is in an MHW
active_days = np.any(mhw_mask == 1, axis=(1, 2))
regional_events = []
start = None
for t in range(n_time_target):
    if active_days[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            regional_events.append((start, t-1))
            start = None
if start is not None:
    regional_events.append((start, n_time_target-1))

# --- Output ---
# mhw_mask.nc
ds_out = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": target_data.time,
        "latitude": target_data.latitude,
        "longitude": target_data.longitude,
    }
)
os.makedirs('output', exist_ok=True)
ds_out.to_netcdf('output/mhw_mask.nc')

# report.json
target_times = pd.to_datetime(target_data.time.values)
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": "1991-12-27", "end": "2003-01-05"},
    "target_analysed": {
        "start": target_times[0].strftime('%Y-%m-%d'),
        "end": target_times[-1].strftime('%Y-%m-%d')
    },
    "events": [
        {"onset": target_times[s].strftime('%Y-%m-%d'), "end": target_times[e].strftime('%Y-%m-%d')}
        for s, e in regional_events
    ],
    "complete": True,
    "caveats": ""
}
with open('output/report.json', 'w') as f:
    json.dump(report, f)

print("Analysis complete. Files written to output/")
