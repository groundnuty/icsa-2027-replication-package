import xarray as xr
import fsspec
import numpy as np
import pandas as pd
import json
from datetime import timedelta

def get_doy(date):
    # 1 Jan = 1, ..., 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[date.month - 1] + date.day

# Params
lat_min, lat_max = 54.13, 55.33
lon_min, lon_max = 14.67, 15.87
baseline_start = pd.Timestamp('1992-01-01')
baseline_end = pd.Timestamp('2002-12-31')
target_start = pd.Timestamp('2004-06-01')
target_end = pd.Timestamp('2004-08-31')

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')

# Slice region
ds_region = ds.sel(
    latitude=slice(lat_min, lat_max),
    longitude=slice(lon_min, lon_max)
)

# Subset time for baseline pool and target
# Baseline dates are 1992-01-01 to 2002-12-31.
# Windows are +/- 5 days.
# Min date: 1992-01-01 - 5 days = 1991-12-27
# Max date: 2002-12-31 + 5 days = 2003-01-05
# Target: 2004-06-01 to 2004-08-31
ds_subset = ds_region.sel(time=slice('1991-12-27', '2004-08-31')).load()
sst = ds_subset['analysed_sst'].astype(np.float64)

# 1. Sea cells: finite SST on every day of target period
target_sst = sst.sel(time=slice(target_start, target_end))
# finite = not nan and not inf
is_finite = np.isfinite(target_sst)
# All days in target period must be finite
sea_mask = is_finite.all(dim='time')

# 2. Threshold and climatology
# Baseline dates
baseline_dates = pd.date_range(baseline_start, baseline_end)
# All dates available in the subset for pooling
all_dates = pd.to_datetime(ds_subset.time.values)
date_to_idx = {d: i for i, d in enumerate(all_dates)}

# We only need the threshold/climatology for sea cells.
# But we can compute for all and then mask.
# Let's compute for each cell.
# The region is small (60x60), so we can iterate or use vectorization.
# 60*60 = 3600 cells.
# 366 days of year.

# To optimize, we can pre-calculate the pool of indices for each DOY
doy_pools = {}
for d in range(1, 367):
    if d == 60:
        continue
    
    # Baseline dates with DOY d
    S_d = [date for date in baseline_dates if get_doy(date) == d]
    
    # Pool of dates: union of [D-5, D+5]
    pool_dates = set()
    for D in S_d:
        for delta in range(-5, 6):
            pool_dates.add(D + timedelta(days=delta))
    
    # Convert to indices
    pool_indices = [date_to_idx[d] for d in pool_dates if d in date_to_idx]
    doy_pools[d] = pool_indices

# Pre-allocate arrays
# shape: (366, lat, lon)
thresholds = np.full((366, sst.latitude.size, sst.longitude.size), np.nan)
climatologies = np.full((366, sst.latitude.size, sst.longitude.size), np.nan)

# To avoid loop over cells, we can slice the sst array
sst_values = sst.values # (time, lat, lon)

for d in range(1, 367):
    if d == 60:
        continue
    
    indices = doy_pools[d]
    # Extract values for these dates: (len(indices), lat, lon)
    pool_data = sst_values[indices, :, :]
    
    # Compute 90th percentile (hazen) and mean
    # numpy.nanquantile with method='hazen'
    thresholds[d-1] = np.nanquantile(pool_data, 0.9, axis=0, method='hazen')
    climatologies[d-1] = np.nanmean(pool_data, axis=0)

# Handle day 60
thresholds[59] = (thresholds[58] + thresholds[60]) / 2
climatologies[59] = (climatologies[58] + climatologies[60]) / 2

# Smoothing: 31-day centered moving mean (modulo 366)
def smooth(arr):
    # arr shape: (366, lat, lon)
    smoothed = np.zeros_like(arr)
    for i in range(366):
        # indices from i-15 to i+15 modulo 366
        indices = [(i + k) % 366 for k in range(-15, 16)]
        # arr[indices] shape: (31, lat, lon)
        smoothed[i] = np.nanmean(arr[indices], axis=0)
    return smoothed

thresholds = smooth(thresholds)
climatologies = smooth(climatologies)

# 3. Per-cell MHWs
# Target period SST and thresholds
target_sst_vals = target_sst.values # (time, lat, lon)
target_times = pd.to_datetime(target_sst.time.values)

# Get thresholds for target days
target_thresholds = []
for t in target_times:
    d = get_doy(t)
    target_thresholds.append(thresholds[d-1])
target_thresholds = np.array(target_thresholds) # (time, lat, lon)

# Hot days
# SST >= threshold
is_hot = (target_sst_vals >= target_thresholds)
# Land cells are not hot
is_hot = is_hot & sea_mask.values

# Find MHWs: runs of >= 5 hot days, joined by 1-2 non-hot days
# Iterate over each cell
mhw_mask = np.zeros_like(is_hot, dtype=np.uint8)
n_time, n_lat, n_lon = is_hot.shape

for lat in range(n_lat):
    for lon in range(n_lon):
        cell_hot = is_hot[:, lat, lon]
        if not np.any(cell_hot):
            continue
            
        # Identify runs of hot days
        # Using a simple state machine or grouping
        runs = []
        start = None
        for i in range(n_time):
            if cell_hot[i]:
                if start is None:
                    start = i
            else:
                if start is not None:
                    runs.append((start, i - 1))
                    start = None
        if start is not None:
            runs.append((start, n_time - 1))
            
        # Keep only runs >= 5 days
        mhw_runs = [r for r in runs if (r[1] - r[0] + 1) >= 5]
        
        # Join runs separated by 1 or 2 non-hot days
        if not mhw_runs:
            continue
            
        joined_runs = []
        if mhw_runs:
            curr_start, curr_end = mhw_runs[0]
            for i in range(1, len(mhw_runs)):
                next_start, next_end = mhw_runs[i]
                if next_start - curr_end - 1 <= 2:
                    curr_end = next_end
                else:
                    joined_runs.append((curr_start, curr_end))
                    curr_start, curr_end = next_start, next_end
            joined_runs.append((curr_start, curr_end))
            
        for start, end in joined_runs:
            mhw_mask[start:end+1, lat, lon] = 1

# 4. Regional events
# Day is active if at least one sea cell is in an MHW
is_active = np.any(mhw_mask == 1, axis=(1, 2))

# Regional MHW events: maximal runs of active days
events = []
start = None
for i in range(n_time):
    if is_active[i]:
        if start is None:
            start = i
    else:
        if start is not None:
            events.append((target_times[start], target_times[i-1]))
            start = None
if start is not None:
    events.append((target_times[start], target_times[n_time-1]))

# Outputs
# mhw_mask.nc
# Dimensions: time, lat, lon
# Coordinates: target_sst.time, target_sst.latitude, target_sst.longitude
mhw_ds = xr.Dataset(
    {"mhw": (("time", "latitude", "longitude"), mhw_mask)},
    coords={
        "time": target_sst.time,
        "latitude": target_sst.latitude,
        "longitude": target_sst.longitude
    }
)
mhw_ds.to_netcdf("output/mhw_mask.nc")

# report.json
report = {
    "region": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
    "baseline_analysed": {"start": baseline_start.strftime('%Y-%m-%d'), "end": baseline_end.strftime('%Y-%m-%d')},
    "target_analysed": {"start": target_start.strftime('%Y-%m-%d'), "end": target_end.strftime('%Y-%m-%d')},
    "events": [{"onset": e[0].strftime('%Y-%m-%d'), "end": e[1].strftime('%Y-%m-%d')} for e in events],
    "complete": True,
    "caveats": ""
}

with open("output/report.json", "w") as f:
    json.dump(report, f)

print("Success")
