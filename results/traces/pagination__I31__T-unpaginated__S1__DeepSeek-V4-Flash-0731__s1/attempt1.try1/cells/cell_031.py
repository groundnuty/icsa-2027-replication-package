
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

# ====== Configuration ======
lat_start, lat_end = 260, 319
lon_start, lon_end = 485, 544
n_lat, n_lon = 60, 60

# Day of year mapping
month_offsets = {1: 0, 2: 31, 3: 60, 4: 91, 5: 121, 6: 152, 7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335}
def date_to_doy(y, m, d):
    return month_offsets[m] + d

# ====== Generate dates ======
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

# ====== Load baseline data ======
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

# ====== Load target data ======
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

# ====== Build doy -> pool indices ======
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

# ====== Compute thresholds and climatology (vectorized) ======
print("Computing thresholds and climatology...")
start = time.time()

threshold = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

for doy in range(1, 367):
    if doy == 60:
        continue
    pool_idx = doy_to_pool_indices[doy]
    pool_data = baseline_sst[pool_idx, :, :]  # (n_pool, 60, 60)
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        threshold[doy-1, :, :] = np.nanpercentile(pool_data, 90, axis=0, method='linear')
        climatology[doy-1, :, :] = np.nanmean(pool_data, axis=0)

print(f"Threshold/climatology computed in {time.time()-start:.1f}s")

# Set doy 60 (index 59) to mean of doy 59 and 61
threshold[59, :, :] = (threshold[58, :, :] + threshold[60, :, :]) / 2.0
climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2.0

print(f"NaN in threshold: {np.isnan(threshold).sum()}")
print(f"NaN in climatology: {np.isnan(climatology).sum()}")

# ====== Smoothing ======
print("Smoothing...")

def smooth_wrap(arr):
    """Smooth a (366, ...) array with 31-day centred moving mean wrapping around."""
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

print(f"Smoothed threshold NaN count: {np.isnan(threshold_smooth).sum()}")
print(f"Smoothed climatology NaN count: {np.isnan(climatology_smooth).sum()}")

# ====== Determine sea cells ======
sea_cells = np.all(np.isfinite(target_sst), axis=0)
n_sea = sea_cells.sum()
print(f"Sea cells: {n_sea} out of {60*60}")

# Check how many sea cells have valid thresholds for all target doy values
target_doy = np.array([date_to_doy(d.year, d.month, d.day) for d in dates_target])
valid_threshold_for_target = np.all(np.isfinite(threshold_smooth[target_doy-1, :, :]), axis=0)
sea_with_valid_threshold = sea_cells & valid_threshold_for_target
print(f"Sea cells with valid threshold for all target days: {sea_with_valid_threshold.sum()} out of {n_sea}")
print(f"Sea cells WITHOUT valid threshold: {(sea_cells & ~valid_threshold_for_target).sum()}")

# ====== Detect per-cell MHWs ======
print("\nDetecting per-cell MHWs...")

n_target = len(dates_target)

# Determine hot days
hot = np.zeros((n_target, n_lat, n_lon), dtype=bool)
for i in range(n_target):
    doy = target_doy[i]
    hot[i] = target_sst[i] >= threshold_smooth[doy-1]

# Only sea cells can be hot
hot = hot & sea_cells[np.newaxis, :, :]

# Count hot days per cell
hot_count_per_cell = hot.sum(axis=0)
print(f"Hot day count per cell - min: {hot_count_per_cell[sea_cells].min()}, max: {hot_count_per_cell[sea_cells].max()}, mean: {hot_count_per_cell[sea_cells].mean():.1f}")
print(f"Cells with any hot days: {(hot_count_per_cell > 0).sum()}")

# Find per-cell MHWs
cell_mhw_mask = np.zeros((n_target, n_lat, n_lon), dtype=bool)

for i in range(n_lat):
    for j in range(n_lon):
        if not sea_cells[i, j]:
            continue
        hot_series = hot[:, i, j]
        
        # Find runs of hot days
        runs = []
        run_start = None
        for t in range(n_target):
            if hot_series[t]:
                if run_start is None:
                    run_start = t
            else:
                if run_start is not None:
                    runs.append((run_start, t-1))
                    run_start = None
        if run_start is not None:
            runs.append((run_start, n_target-1))
        
        # Filter runs of length >= 5
        long_runs = [r for r in runs if r[1] - r[0] + 1 >= 5]
        
        if not long_runs:
            continue
        
        # Join runs separated by 1-2 non-hot days
        merged_runs = []
        current = long_runs[0]
        for next_run in long_runs[1:]:
            gap = next_run[0] - current[1] - 1
            if gap <= 2:
                current = (current[0], next_run[1])
            else:
                merged_runs.append(current)
                current = next_run
        merged_runs.append(current)
        
        # Mark cells
        for (s, e) in merged_runs:
            cell_mhw_mask[s:e+1, i, j] = True

n_cells_with_mhw = cell_mhw_mask.any(axis=0).sum()
print(f"Cells with MHWs: {n_cells_with_mhw}")

# ====== Detect regional events ======
active = np.any(cell_mhw_mask, axis=(1, 2))
print(f"Active days: {active.sum()} out of {n_target}")

events = []
run_start = None
for t in range(n_target):
    if active[t]:
        if run_start is None:
            run_start = t
    else:
        if run_start is not None:
            events.append((run_start, t-1))
            run_start = None
if run_start is not None:
    events.append((run_start, n_target-1))

print(f"Regional events: {len(events)}")
for s, e in events:
    print(f"  {dates_target[s]} to {dates_target[e]}")
    # Print which cells are in MHW on the first active day
    if s < n_target:
        cells_active = np.argwhere(cell_mhw_mask[s])
        print(f"    {len(cells_active)} cells in MHW on {dates_target[s]}")

# ====== Diagnostics ======
# Check some specific cells
print("\n=== Diagnostics ===")
# Find cells with most hot days
if hot_count_per_cell[sea_cells].max() > 0:
    best_cell = np.argwhere(hot_count_per_cell == hot_count_per_cell.max())[0]
    ci, cj = best_cell
    print(f"Cell ({ci},{cj}) has {hot_count_per_cell[ci,cj]} hot days")
    
    # Check threshold and SST for this cell on hot days
    for t in range(n_target):
        if hot[t, ci, cj]:
            doy = target_doy[t]
            print(f"  {dates_target[t]} (doy {doy}): SST={target_sst[t,ci,cj]:.2f}, threshold={threshold_smooth[doy-1,ci,cj]:.2f}")

# Check if thresholds are very high compared to target SST for all cells
print("\nChecking threshold vs SST margins...")
for ci in [0, 10, 20, 30]:
    for cj in [0, 10, 20, 30]:
        if sea_cells[ci, cj]:
            # Compute average difference between target SST and threshold
            diffs = []
            for t in range(n_target):
                doy = target_doy[t]
                if np.isfinite(threshold_smooth[doy-1, ci, cj]):
                    diffs.append(target_sst[t, ci, cj] - threshold_smooth[doy-1, ci, cj])
            if diffs:
                print(f"  Cell ({ci},{cj}): avg SST-threshold = {np.mean(diffs):.2f}K, min = {np.min(diffs):.2f}K")

# ====== Write output files ======
print("\nWriting output files...")

# Get lat/lon values
f = fs.open(f'{base_path}/sst_19820101.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lat_vals = ds.latitude.values[lat_start:lat_end+1]
lon_vals = ds.longitude.values[lon_start:lon_end+1]
ds.close()

os.makedirs('output', exist_ok=True)

# Write mhw_mask.nc
mhw_mask = cell_mhw_mask.astype(np.uint8)

ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': np.array([np.datetime64(d) for d in dates_target]),
        'lat': lat_vals,
        'lon': lon_vals
    }
)
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Wrote output/mhw_mask.nc")

# Write report.json
report = {
    'region': {
        'lat_min': 58.69,
        'lat_max': 59.89,
        'lon_min': 18.69,
        'lon_max': 19.89
    },
    'baseline_analysed': {
        'start': str(dates_baseline[0]),
        'end': str(dates_baseline[-1])
    },
    'target_analysed': {
        'start': str(dates_target[0]),
        'end': str(dates_target[-1])
    },
    'events': [
        {'onset': str(dates_target[s]), 'end': str(dates_target[e])}
        for s, e in events
    ],
    'complete': True,
    'caveats': ''
}

with open('output/report.json', 'w') as fout:
    json.dump(report, fout, indent=2)

print("Wrote output/report.json")
print("Done!")
