
import numpy as np
import pandas as pd

# Load data
baseline_sst = np.load('/work/baseline_sst.npy')
target_sst = np.load('/work/target_sst.npy')
baseline_times = np.load('/work/baseline_times.npy')
target_times = np.load('/work/target_times.npy')
baseline_pd = pd.to_datetime(baseline_times)
target_pd = pd.to_datetime(target_times)

def doy(date):
    dt = pd.Timestamp(date)
    month = dt.month
    day = dt.day
    month_lengths = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_lengths[:month-1]) + day

baseline_doy = np.array([doy(d) for d in baseline_pd])

# Identify sea cells
n_time, n_lat, n_lon = target_sst.shape
sea_cells = np.all(np.isfinite(target_sst), axis=0)

# Build pools for each DOY
baseline_core_start = pd.Timestamp('1992-01-01')
baseline_core_end = pd.Timestamp('2002-12-31')
is_core = (baseline_pd >= baseline_core_start) & (baseline_pd <= baseline_core_end)
core_indices = np.where(is_core)[0]

pools = {}
for d in range(1, 367):
    if d == 60:
        pools[d] = None
        continue
    
    matching_core = core_indices[baseline_doy[core_indices] == d]
    
    if len(matching_core) == 0:
        pools[d] = []
        continue
    
    pool_indices = set()
    for idx in matching_core:
        date = baseline_pd[idx]
        start = date - pd.Timedelta(days=5)
        end = date + pd.Timedelta(days=5)
        mask = (baseline_pd >= start) & (baseline_pd <= end)
        idxs = np.where(mask)[0]
        pool_indices.update(idxs)
    
    pools[d] = sorted(pool_indices)

# Store as 367-size array where index = DOY (1-366 used, 0 unused)
thresholds = np.full((367, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((367, n_lat, n_lon), np.nan, dtype=np.float64)

sea_indices = np.where(sea_cells)
sea_pairs = list(zip(sea_indices[0], sea_indices[1]))
print(f"Processing {len(sea_pairs)} sea cells...")

# Process each sea cell
for idx, (lat_i, lon_i) in enumerate(sea_pairs):
    if idx % 500 == 0:
        print(f"  Processing cell {idx}/{len(sea_pairs)}...")
    
    cell_sst = baseline_sst[:, lat_i, lon_i]
    
    for d in range(1, 367):
        if d == 60:
            continue
        
        pool_idx = pools[d]
        if len(pool_idx) == 0:
            continue
        
        pool_values = cell_sst[pool_idx]
        valid = pool_values[np.isfinite(pool_values)]
        
        if len(valid) == 0:
            continue
        
        thresholds[d, lat_i, lon_i] = np.percentile(valid, 90, method='hazen')
        climatology[d, lat_i, lon_i] = np.mean(valid)
    
    # Day 60: mean of days 59 and 61
    if np.isfinite(thresholds[59, lat_i, lon_i]) and np.isfinite(thresholds[61, lat_i, lon_i]):
        thresholds[60, lat_i, lon_i] = (thresholds[59, lat_i, lon_i] + thresholds[61, lat_i, lon_i]) / 2
        climatology[60, lat_i, lon_i] = (climatology[59, lat_i, lon_i] + climatology[61, lat_i, lon_i]) / 2

print("Done computing raw thresholds and climatology.")

# Check for missing values
missing_thresh = np.sum(np.isnan(thresholds[1:]), axis=0)  # exclude index 0
missing_clim = np.sum(np.isnan(climatology[1:]), axis=0)

print(f"Cells with missing thresholds: {np.sum(missing_thresh > 0)}")
print(f"Cells with 0 missing thresholds: {np.sum(missing_thresh == 0)}")
print(f"Max missing thresholds in any cell: {missing_thresh.max()}")
print(f"Cells with missing climatology: {np.sum(missing_clim > 0)}")

np.save('/work/thresholds_raw.npy', thresholds)
np.save('/work/climatology_raw.npy', climatology)
print("Saved raw thresholds and climatology.")
