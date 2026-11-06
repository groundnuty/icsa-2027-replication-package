import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

# Reload data
baseline_data = np.load('/work/baseline_data.npy').astype(np.float64)
target_data = np.load('/work/target_data.npy').astype(np.float64)

# Sea cells: finite on all target days
sea_mask = np.all(~np.isnan(target_data), axis=0)
sea_cells = np.argwhere(sea_mask)  # (N, 2) array of (i, j)
print(f"Sea cells: {len(sea_cells)}")

# Day-of-year mapping
def day_of_year(month, day):
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(month_days[:month-1]) + day

# Generate all extraction dates
start = datetime(1991, 12, 27)
end = datetime(2003, 1, 5)
all_dates = []
d = start
while d <= end:
    all_dates.append(d)
    d += timedelta(days=1)

# Baseline dates
base_start = datetime(1992, 1, 1)
base_end = datetime(2002, 12, 31)
baseline_dates = [dt for dt in all_dates if base_start <= dt <= base_end]
baseline_doy = [day_of_year(dt.month, dt.day) for dt in baseline_dates]

# Build pools
base_idx_in_all = [all_dates.index(dt) for dt in baseline_dates]
doy_pool_indices = defaultdict(list)
for k, doy in enumerate(baseline_doy):
    if doy == 60:
        continue
    bidx = base_idx_in_all[k]
    for i in range(max(0, bidx - 5), min(len(all_dates), bidx + 6)):
        doy_pool_indices[doy].append(i)
for doy in doy_pool_indices:
    doy_pool_indices[doy] = sorted(set(doy_pool_indices[doy]))

# Initialize arrays: threshold and climatology for all 60x60 cells
# We'll compute for all cells (including land) then use only sea cells
threshold = np.zeros((60, 60, 366), dtype=np.float64)
climatology = np.zeros((60, 60, 366), dtype=np.float64)

# Compute for each day-of-year
for doy in range(1, 367):
    if doy == 60:
        continue
    pool_idx = doy_pool_indices[doy]
    pool_data = baseline_data[pool_idx]  # (len(pool_idx), 60, 60)
    # Compute percentile and mean ignoring NaN
    with np.errstate(all='ignore'):
        p = np.nanpercentile(pool_data, 90, axis=0, method='hazen')
        m = np.nanmean(pool_data, axis=0)
    threshold[:, :, doy-1] = p
    climatology[:, :, doy-1] = m

# Set day 60 (index 59) to mean of days 59 (index 58) and 61 (index 60)
threshold[:, :, 59] = (threshold[:, :, 58] + threshold[:, :, 60]) / 2.0
climatology[:, :, 59] = (climatology[:, :, 58] + climatology[:, :, 60]) / 2.0

print("Threshold and climatology computed")
print("Threshold shape:", threshold.shape)
print("Climatology shape:", climatology.shape)

# Verify some values
print(f"Sample threshold (cell 0,0, DOY 1): {threshold[0, 0, 0]}")
print(f"Sample climatology (cell 0,0, DOY 1): {climatology[0, 0, 0]}")
print(f"Day 60 threshold (cell 0,0): {threshold[0, 0, 59]}")
print(f"Day 59 threshold (cell 0,0): {threshold[0, 0, 58]}")
print(f"Day 61 threshold (cell 0,0): {threshold[0, 0, 60]}")

# Save intermediate results
np.save('/work/threshold_raw.npy', threshold)
np.save('/work/climatology_raw.npy', climatology)
print("Intermediate results saved")
