
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

# Build pools for each DOY (using the full baseline data, not just sea cells)
# We need to do this per cell anyway, since different cells may have different NaN patterns

# First, let's build the pool indices for each DOY
baseline_core_start = pd.Timestamp('1992-01-01')
baseline_core_end = pd.Timestamp('2002-12-31')
is_core = (baseline_pd >= baseline_core_start) & (baseline_pd <= baseline_core_end)
core_indices = np.where(is_core)[0]

# Build pool for each DOY
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

# Compute thresholds and climatology for each sea cell
n_doy = 366
n_cells = sea_cells.sum()

# Store results as 2D arrays: (366, n_lat*n_lon) for all cells
# We'll fill in only sea cells
thresholds = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((366, n_lat, n_lon), np.nan, dtype=np.float64)

# Get sea cell indices
sea_indices = np.where(sea_cells)
sea_pairs = list(zip(sea_indices[0], sea_indices[1]))
print(f"Processing {len(sea_pairs)} sea cells...")

# Process each sea cell
for idx, (lat_i, lon_i) in enumerate(sea_pairs):
    if idx % 500 == 0:
        print(f"  Processing cell {idx}/{len(sea_pairs)}...")
    
    # Get SST for this cell across all baseline days
    cell_sst = baseline_sst[:, lat_i, lon_i]
    
    # Compute threshold and climatology for each DOY
    for d in range(1, 367):
        if d == 60:
            continue
        
        pool_idx = pools[d]
        if len(pool_idx) == 0:
            continue
        
        pool_values = cell_sst[pool_idx]
        # Ignore NaN
        valid = pool_values[np.isfinite(pool_values)]
        
        if len(valid) == 0:
            continue
        
        # Threshold: 90th percentile, hazen method
        thresholds[d, lat_i, lon_i] = np.percentile(valid, 90, method='hazen')
        
        # Climatology: mean
        climatology[d, lat_i, lon_i] = np.mean(valid)
    
    # Set day 60 as mean of days 59 and 61
    if np.isfinite(thresholds[59, lat_i, lon_i]) and np.isfinite(thresholds[61, lat_i, lon_i]):
        thresholds[60, lat_i, lon_i] = (thresholds[59, lat_i, lon_i] + thresholds[61, lat_i, lon_i]) / 2
        climatology[60, lat_i, lon_i] = (climatology[59, lat_i, lon_i] + climatology[61, lat_i, lon_i]) / 2

print("Done computing raw thresholds and climatology.")

# Check for cells that might have gaps in their DOY data
# For sea cells, we need all DOYs to have valid values
missing_doy = np.sum(np.isnan(thresholds), axis=0)
print(f"Cells with missing thresholds: {np.sum(missing_doy > 0)}")
print(f"Cells with 0 missing: {np.sum(missing_doy == 0)}")
print(f"Max missing DOYs in any cell: {missing_doy.max()}")

np.save('/work/thresholds_raw.npy', thresholds)
np.save('/work/climatology_raw.npy', climatology)
