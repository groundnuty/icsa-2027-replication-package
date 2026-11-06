
# Let me verify that the result is correct by doing a focused analysis
# on a few cells where hot days were detected
# I'll check if any cell has 5+ consecutive hot days

# First, let me reload the data and re-run with hazen
# But let me also save intermediate data for verification

import fsspec
import xarray as xr
import numpy as np
import datetime as dt
import time
import json
import os
import warnings

fs = fsspec.filesystem('onedata')
base_path = 'icsa2027_data_20261101T090944Z/s1z'

lat_start, lat_end = 260, 319
lon_start, lon_end = 485, 544
n_lat, n_lon = 60, 60

month_offsets = {1: 0, 2: 31, 3: 60, 4: 91, 5: 121, 6: 152, 7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335}
def date_to_doy(y, m, d):
    return month_offsets[m] + d

# Generate dates
dates_baseline = []
d = dt.date(1991, 12, 27)
while d <= dt.date(2003, 1, 5):
    dates_baseline.append(d)
    d += dt.timedelta(days=1)

dates_target = []
d = dt.date(2017, 6, 1)
while d <= dt.date(2017, 8, 31):
    dates_target.append(d)
    d += dt.timedelta(days=1)

print(f"Baseline dates: {len(dates_baseline)}, Target dates: {len(dates_target)}")

# Load baseline data
print("Loading baseline data...")
start = time.time()
baseline_sst = np.full((len(dates_baseline), n_lat, n_lon), np.nan, dtype=np.float64)
for i, date in enumerate(dates_baseline):
    fname = f"sst_{date.year:04d}{date.month:02d}{date.day:02d}.nc"
    f = fs.open(f'{base_path}/{fname}', 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    baseline_sst[i] = ds.analysed_sst.values[0, lat_start:lat_end+1, lon_start:lon_end+1].astype(np.float64)
    ds.close()
print(f"Baseline loaded in {time.time()-start:.1f}s")

# Load target data
print("Loading target data...")
start = time.time()
target_sst = np.full((len(dates_target), n_lat, n_lon), np.nan, dtype=np.float64)
for i, date in enumerate(dates_target):
    fname = f"sst_{date.year:04d}{date.month:02d}{date.day:02d}.nc"
    f = fs.open(f'{base_path}/{fname}', 'rb')
    ds = xr.open_dataset(f, engine='h5netcdf')
    target_sst[i] = ds.analysed_sst.values[0, lat_start:lat_end+1, lon_start:lon_end+1].astype(np.float64)
    ds.close()
print(f"Target loaded in {time.time()-start:.1f}s")

# Build doy -> pool indices
doy_to_baseline_dates = {d: [] for d in range(1, 367)}
d = dt.date(1992, 1, 1)
while d <= dt.date(2002, 12, 31):
    doy = date_to_doy(d.year, d.month, d.day)
    doy_to_baseline_dates[doy].append(d)
    d += dt.timedelta(days=1)

doy_to_pool_dates = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool_dates = set()
    for B in doy_to_baseline_dates[doy]:
        for offset in range(-5, 6):
            pool_dates.add(B + dt.timedelta(days=offset))
    doy_to_pool_dates[doy] = sorted(pool_dates)

date_to_index = {date: i for i, date in enumerate(dates_baseline)}
doy_to_pool_indices = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    indices = [date_to_index[d] for d in doy_to_pool_dates[doy]]
    doy_to_pool_indices[doy] = np.array(indices)

# Compute thresholds and climatology using method='hazen' (as instructed)
print("Computing thresholds with method='hazen'...")
start = time.time()

threshold = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

for doy in range(1, 367):
    if doy == 60:
        continue
    pool_idx = doy_to_pool_indices[doy]
    pool_data = baseline_sst[pool_idx, :, :]
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        threshold[doy-1, :, :] = np.nanpercentile(pool_data, 90, axis=0, method='hazen')
        climatology[doy-1, :, :] = np.nanmean(pool_data, axis=0)

print(f"Threshold/climatology computed in {time.time()-start:.1f}s")

# Set doy 60
threshold[59, :, :] = (threshold[58, :, :] + threshold[60, :, :]) / 2.0
climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2.0

# Smooth
def smooth_wrap(arr):
    result = np.full_like(arr, np.nan, dtype=np.float64)
    n = arr.shape[0]
    padded = np.concatenate([arr[-15:], arr, arr[:15]], axis=0)
    for d in range(n):
        window = padded[d:d+31]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result[d] = np.nanmean(window, axis=0)
    return result

threshold_smooth = smooth_wrap(threshold)
climatology_smooth = smooth_wrap(climatology)

# Sea cells
sea_cells = np.all(np.isfinite(target_sst), axis=0)
print(f"Sea cells: {sea_cells.sum()}")

# Hot days
target_doy = np.array([date_to_doy(d.year, d.month, d.day) for d in dates_target])
n_target = len(dates_target)
hot = np.zeros((n_target, n_lat, n_lon), dtype=bool)
for i in range(n_target):
    doy = target_doy[i]
    hot[i] = target_sst[i] >= threshold_smooth[doy-1]
hot = hot & sea_cells[np.newaxis, :, :]

# Count hot days
hot_count = hot.sum(axis=0)
print(f"Hot days per cell: min={hot_count[sea_cells].min()}, max={hot_count[sea_cells].max()}, cells with any={np.sum(hot_count > 0)}")

# Find cells with max hot days and check their patterns
print("\nChecking cells with hot day patterns...")
max_cells = np.argwhere(hot_count == hot_count.max())
for ci, cj in max_cells[:10]:
    hot_days = np.where(hot[:, ci, cj])[0]
    print(f"  Cell ({ci},{cj}): {len(hot_days)} hot days at indices {hot_days}")
    # Check if any run of >= 5 consecutive
    runs = []
    if len(hot_days) > 0:
        run_start = hot_days[0]
        prev = hot_days[0]
        for t in hot_days[1:]:
            if t - prev > 1:
                runs.append((run_start, prev))
                run_start = t
            prev = t
        runs.append((run_start, prev))
    print(f"    Runs: {runs}")
    long_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
    print(f"    Long runs (>=5): {long_runs}")

# Check cells with 4+ hot days
print("\nCells with 4+ hot days:")
cells_4plus = np.argwhere(hot_count >= 4)
print(f"  Count: {len(cells_4plus)}")
for ci, cj in cells_4plus[:5]:
    hot_days = np.where(hot[:, ci, cj])[0]
    # Check consecutive runs
    runs = []
    if len(hot_days) > 0:
        run_start = hot_days[0]
        prev = hot_days[0]
        for t in hot_days[1:]:
            if t - prev > 1:
                runs.append((run_start, prev))
                run_start = t
            prev = t
        runs.append((run_start, prev))
    print(f"  Cell ({ci},{cj}): hot days at {hot_days}, runs={runs}")
    # Check if joined runs would be >= 5
    if len(runs) >= 2:
        for k in range(len(runs)-1):
            gap = runs[k+1][0] - runs[k][1] - 1
            if gap <= 2:
                print(f"    Gap between runs {runs[k]} and {runs[k+1]}: {gap} days - WOULD BE JOINED")
