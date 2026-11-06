
import numpy as np
from datetime import datetime, timedelta

def doy_fixed(dt):
    month_offsets = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_offsets[dt.month - 1] + dt.day

# Load data
base_sst = np.load('/work/base_sst.npy')  # (4028, 60, 60)
target_sst = np.load('/work/target_sst.npy')  # (92, 60, 60)
base_times = np.load('/work/base_times.npy')
target_times = np.load('/work/target_times.npy')

# Compute sea cells
sea_cells = np.all(np.isfinite(target_sst), axis=0)  # (60, 60)
n_sea = sea_cells.sum()
sea_indices = np.where(sea_cells)
print(f"Sea cells: {n_sea}")

# Build pool indices
base_dates = []
for t in base_times:
    dt = datetime.utcfromtimestamp(t.astype('datetime64[s]').astype(np.int64))
    base_dates.append(dt)
base_dates = np.array(base_dates)

baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)
is_baseline = np.array([(d >= baseline_start) and (d <= baseline_end) for d in base_dates])
baseline_indices = np.where(is_baseline)[0]
base_doy = np.array([doy_fixed(d) for d in base_dates[baseline_indices]])

from collections import defaultdict
doy_to_baseline_idx = defaultdict(list)
for idx, d in zip(baseline_indices, base_doy):
    doy_to_baseline_idx[d].append(idx)

pool_indices = {}
for d in range(1, 367):
    if d == 60:
        continue
    pool_dates = set()
    for j in doy_to_baseline_idx[d]:
        for delta in range(-5, 6):
            idx = j + delta
            if 0 <= idx < len(base_dates):
                pool_dates.add(idx)
    pool_indices[d] = sorted(pool_dates)

# Extract sea cell data
# base_sst_sea: (4028, n_sea)
base_sst_sea = base_sst[:, sea_cells]  # (4028, n_sea)

# Compute threshold and climatology for each day of year
threshold = np.full((n_sea, 366), np.nan)  # (n_sea, 366)
climatology = np.full((n_sea, 366), np.nan)

for d in range(1, 367):
    if d == 60:
        continue
    pool_idx = pool_indices[d]
    pool_values = base_sst_sea[pool_idx, :]  # (n_pool, n_sea)
    
    # Compute 90th percentile using Hazen method, ignoring NaN
    # threshold[:, d-1] = np.nanpercentile(pool_values, 90, axis=0, method='hazen')
    
    # Actually, numpy's method="hazen" is the default for np.nanpercentile
    # But let me verify
    for i in range(n_sea):
        vals = pool_values[:, i]
        valid = vals[~np.isnan(vals)]
        if len(valid) > 0:
            threshold[i, d-1] = np.percentile(valid, 90, method='hazen')
            climatology[i, d-1] = np.mean(valid)
        else:
            threshold[i, d-1] = np.nan
            climatology[i, d-1] = np.nan

print("Threshold computed, NaN count:", np.isnan(threshold).sum())
print("Climatology computed, NaN count:", np.isnan(climatology).sum())

# Set day 60 (index 59) to mean of days 59 and 61 (indices 58 and 60)
threshold[:, 59] = (threshold[:, 58] + threshold[:, 60]) / 2
climatology[:, 59] = (climatology[:, 58] + climatology[:, 60]) / 2

print("After day 60 fill, NaN count:", np.isnan(threshold).sum(), np.isnan(climatology).sum())

# Save intermediate results
np.save('/work/threshold_raw.npy', threshold)
np.save('/work/climatology_raw.npy', climatology)
np.save('/work/sea_cells.npy', sea_cells)
print("Saved raw threshold and climatology")
