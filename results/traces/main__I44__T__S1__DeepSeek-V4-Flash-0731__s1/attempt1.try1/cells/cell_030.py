import numpy as np
import xarray as xr
import datetime as dt
import pandas as pd
from collections import defaultdict
import json
import os

# ============================================================
# Load data
# ============================================================
base_ds = xr.open_dataset('/tmp/base_data.nc')
target_ds = xr.open_dataset('/tmp/target_data.nc')
base_sst = base_ds['analysed_sst'].values.astype(np.float64)  # (4028, 60, 60)
target_sst = target_ds['analysed_sst'].values.astype(np.float64)  # (92, 60, 60)
base_time = base_ds['time'].values
target_time = target_ds['time'].values
lat_vals = base_ds['latitude'].values  # (60,)
lon_vals = base_ds['longitude'].values  # (60,)

base_dates = [pd.Timestamp(t).to_pydatetime().date() for t in base_time]
target_dates = [pd.Timestamp(t).to_pydatetime().date() for t in target_time]

print(f"Base: {len(base_dates)} days, {base_dates[0]} to {base_dates[-1]}")
print(f"Target: {len(target_dates)} days, {target_dates[0]} to {target_dates[-1]}")
print(f"Lat range: {lat_vals[0]} to {lat_vals[-1]}, n={len(lat_vals)}")
print(f"Lon range: {lon_vals[0]} to {lon_vals[-1]}, n={len(lon_vals)}")

# ============================================================
# Step 1: Day of year mapping
# ============================================================
def day_of_year(date):
    """Map date to day of year 1-366.
    1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366.
    Non-leap years have no day 60.
    """
    y = date.year
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    month_days = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(month_days[:date.month-1]) + date.day
    if not is_leap and date.month >= 3:
        doy += 1
    return doy

# Verify
assert day_of_year(dt.date(1992, 1, 1)) == 1
assert day_of_year(dt.date(1992, 2, 28)) == 59
assert day_of_year(dt.date(1992, 2, 29)) == 60
assert day_of_year(dt.date(1992, 3, 1)) == 61
assert day_of_year(dt.date(1992, 12, 31)) == 366
assert day_of_year(dt.date(1993, 2, 28)) == 59
assert day_of_year(dt.date(1993, 3, 1)) == 61
assert day_of_year(dt.date(1993, 12, 31)) == 366

# ============================================================
# Step 2: Identify baseline dates and build pools
# ============================================================
baseline_start = dt.date(1992, 1, 1)
baseline_end = dt.date(2002, 12, 31)

# Group baseline dates by day of year
baseline_dates_by_doy = defaultdict(list)
for date in base_dates:
    if baseline_start <= date <= baseline_end:
        d = day_of_year(date)
        baseline_dates_by_doy[d].append(date)

# Build mapping from date to index in base_dates
date_to_idx = {d: i for i, d in enumerate(base_dates)}

# For each DOY d (1-366, d != 60), build the pool
pool_indices = defaultdict(set)
for d, dates in baseline_dates_by_doy.items():
    if d == 60:
        continue
    for b in dates:
        for delta in range(-5, 6):
            t = b + dt.timedelta(days=delta)
            if t in date_to_idx:
                pool_indices[d].add(date_to_idx[t])

# Verify all DOYs except 60 have pools
missing = set(range(1, 367)) - set(pool_indices.keys()) - {60}
assert len(missing) == 0, f"Missing pools for DOYs: {missing}"

# ============================================================
# Step 3: Sea cells
# ============================================================
sea_mask = np.all(np.isfinite(target_sst), axis=0)  # (60, 60)
print(f"Sea cells: {sea_mask.sum()}")

# ============================================================
# Step 4: Compute threshold and climatology per cell and DOY
# ============================================================
n_lat, n_lon = 60, 60

# Arrays indexed by DOY 1-366 (index 0 unused)
threshold = np.full((367, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((367, n_lat, n_lon), np.nan, dtype=np.float64)

# Pre-compute for sea cells only
sea_indices = np.argwhere(sea_mask)  # (n_sea, 2)

for d in range(1, 367):
    if d == 60:
        continue
    idxs = sorted(pool_indices[d])
    pool_sst = base_sst[idxs, :, :]  # (n_pool, 60, 60)
    
    for i, j in sea_indices:
        vals = pool_sst[:, i, j]
        vals = vals[np.isfinite(vals)]
        if len(vals) == 0:
            continue
        threshold[d, i, j] = np.quantile(vals, 0.9, method='hazen')
        climatology[d, i, j] = np.mean(vals)

# Day 60: mean of days 59 and 61
threshold[60, :, :] = (threshold[59, :, :] + threshold[61, :, :]) / 2.0
climatology[60, :, :] = (climatology[59, :, :] + climatology[61, :, :]) / 2.0

# Verify no NaN for sea cells
nan_thresh = np.sum(~np.isfinite(threshold[1:367, sea_mask]))
nan_clim = np.sum(~np.isfinite(climatology[1:367, sea_mask]))
print(f"NaN in threshold for sea cells: {nan_thresh}")
print(f"NaN in climatology for sea cells: {nan_clim}")

# ============================================================
# Step 5: Smoothing with 31-day centred moving mean (wrapping)
# ============================================================
def smooth_366(arr_366):
    """Smooth a 366-element array with an unweighted centred 31-day moving mean
    that wraps around the year. arr_366[d] = value at DOY d+1 (0-indexed)."""
    extended = np.concatenate([arr_366[-15:], arr_366, arr_366[:15]])
    smoothed = np.zeros(366, dtype=np.float64)
    for i in range(366):
        smoothed[i] = np.mean(extended[i:i+31])
    return smoothed

threshold_smooth = np.full((367, n_lat, n_lon), np.nan, dtype=np.float64)
climatology_smooth = np.full((367, n_lat, n_lon), np.nan, dtype=np.float64)

for i, j in sea_indices:
    threshold_smooth[1:367, i, j] = smooth_366(threshold[1:367, i, j])
    climatology_smooth[1:367, i, j] = smooth_366(climatology[1:367, i, j])

# Also handle land cells (they don't need threshold/climatology, but set to NaN)

# ============================================================
# Step 6: Per-cell MHW detection
# ============================================================
target_doy = [day_of_year(d) for d in target_dates]
n_time = len(target_dates)

# Hot day detection
hot = np.zeros((n_time, n_lat, n_lon), dtype=bool)
for t in range(n_time):
    doy = target_doy[t]
    hot[t] = target_sst[t] >= threshold_smooth[doy]

# Apply sea mask (land cells are not hot)
hot &= sea_mask[np.newaxis, :, :]

# Per-cell MHW detection
mhw = np.zeros((n_time, n_lat, n_lon), dtype=bool)

for i, j in sea_indices:
    h = hot[:, i, j]
    
    # Find all runs of consecutive hot days
    runs = []
    start = None
    for t in range(n_time):
        if h[t]:
            if start is None:
                start = t
        else:
            if start is not None:
                runs.append((start, t-1))
                start = None
    if start is not None:
        runs.append((start, n_time-1))
    
    # Keep only runs of length >= 5
    long_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
    
    if not long_runs:
        continue
    
    # Join runs separated by 1 or 2 non-hot days
    joined = []
    current = long_runs[0]
    for r in long_runs[1:]:
        gap = r[0] - current[1] - 1
        if 1 <= gap <= 2:
            current = (current[0], r[1])
        else:
            joined.append(current)
            current = r
    joined.append(current)
    
    # Mark MHW days
    for start, end in joined:
        mhw[start:end+1, i, j] = True

print(f"Cells with MHWs: {np.any(mhw, axis=0).sum()}")
print(f"Per-cell MHW day count: {mhw.sum()}")

# ============================================================
# Step 7: Regional events
# ============================================================
active = np.any(mhw, axis=(1, 2))  # (n_time,)
print(f"Active days: {active.sum()}")

events = []
start = None
for t in range(n_time):
    if active[t]:
        if start is None:
            start = t
    else:
        if start is not None:
            events.append((start, t-1))
            start = None
if start is not None:
    events.append((start, n_time-1))

print(f"Regional events: {len(events)}")
for s, e in events:
    print(f"  {target_dates[s]} to {target_dates[e]} ({e-s+1} days)")

# ============================================================
# Step 8: Write output files
# ============================================================
os.makedirs('output', exist_ok=True)

# mhw_mask.nc
mhw_uint8 = mhw.astype(np.uint8)  # (time, lat, lon)

# Create xarray Dataset with dataset's coordinate values
mhw_ds = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_uint8)
    },
    coords={
        'time': target_time,
        'lat': lat_vals,
        'lon': lon_vals,
    },
    attrs={
        'mhw': '1 where the cell is inside a per-cell MHW on that day, 0 otherwise'
    }
)
mhw_ds['mhw'].attrs['units'] = '1'
mhw_ds['mhw'].attrs['long_name'] = 'marine heatwave mask'

mhw_ds.to_netcdf('output/mhw_mask.nc')
print("Wrote output/mhw_mask.nc")

# report.json
report = {
    'region': {
        'lat_min': 63.31,
        'lat_max': 64.51,
        'lon_min': 21.31,
        'lon_max': 22.51,
    },
    'baseline_analysed': {
        'start': '1991-12-27',
        'end': '2003-01-05',
    },
    'target_analysed': {
        'start': '2004-06-01',
        'end': '2004-08-31',
    },
    'events': [
        {'onset': target_dates[s].strftime('%Y-%m-%d'), 'end': target_dates[e].strftime('%Y-%m-%d')}
        for s, e in events
    ],
    'complete': True,
    'caveats': '',
}

with open('output/report.json', 'w') as f:
    json.dump(report, f, indent=2)
print("Wrote output/report.json")
print(json.dumps(report, indent=2))
