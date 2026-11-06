
import numpy as np
from datetime import date, timedelta
import time

# Load the baseline data
baseline_sst = np.load('baseline_sst.npy')  # (4028, 60, 60) float32
sea_mask = np.load('sea_mask.npy')  # (60, 60) bool

print(f"Baseline SST shape: {baseline_sst.shape}")
print(f"Sea mask shape: {sea_mask.shape}")
print(f"Sea cells: {sea_mask.sum()}")

# Rebuild pool indices
def day_of_year_fixed(y, m, d):
    if m == 1:
        return d
    elif m == 2:
        return 31 + d
    else:
        days_before_month = {3: 60, 4: 91, 5: 121, 6: 152, 7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335}
        return days_before_month[m] + d

# Full date range
full_range_start = date(1991, 12, 27)
full_range_end = date(2003, 1, 5)
all_dates = []
d = full_range_start
while d <= full_range_end:
    all_dates.append(d)
    d += timedelta(days=1)
n_dates = len(all_dates)
date_to_idx = {d: i for i, d in enumerate(all_dates)}

# Baseline dates
baseline_start = date(1992, 1, 1)
baseline_end = date(2002, 12, 31)
baseline_dates_by_doy = {}
d = baseline_start
while d <= baseline_end:
    doy = day_of_year_fixed(d.year, d.month, d.day)
    if doy != 60:
        if doy not in baseline_dates_by_doy:
            baseline_dates_by_doy[doy] = []
        baseline_dates_by_doy[doy].append(d)
    d += timedelta(days=1)

# Build pool indices
pool_indices = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    indices = set()
    for bd in baseline_dates_by_doy.get(doy, []):
        for offset in range(-5, 6):
            nd = bd + timedelta(days=offset)
            if full_range_start <= nd <= full_range_end:
                indices.add(date_to_idx[nd])
    pool_indices[doy] = sorted(indices)

print("Pool indices built")

# Now compute threshold and climatology for each sea cell and day-of-year
# Number of sea cells
sea_cells = np.argwhere(sea_mask)
n_sea = len(sea_cells)
print(f"Number of sea cells: {n_sea}")

# Initialize arrays: threshold[366, 60, 60], climatology[366, 60, 60]
# We'll compute these for all cells (including land cells, which will be set to 0 later)
# Actually, we only need them for sea cells, but let's compute for all cells to simplify indexing

threshold = np.zeros((366, 60, 60), dtype=np.float64)
climatology = np.zeros((366, 60, 60), dtype=np.float64)

# For each day of year, compute threshold and climatology for each cell
# The pool for day d includes the same dates for all cells
# So we can do this cell by cell

# For efficiency, let's compute all cells at once for each day-of-year
for doy in range(1, 367):
    if doy == 60:
        continue
    idx = pool_indices[doy]
    if len(idx) == 0:
        continue
    pool_data = baseline_sst[idx].astype(np.float64)  # (n_pool, 60, 60)
    
    # Compute for each cell
    for ci, (lat_i, lon_i) in enumerate(sea_cells):
        values = pool_data[:, lat_i, lon_i]
        finite_vals = values[np.isfinite(values)]
        if len(finite_vals) > 0:
            # 90th percentile using method="hazen" (same as MATLAB quantile default)
            threshold[doy, lat_i, lon_i] = np.quantile(finite_vals, 0.9, method='hazen')
            climatology[doy, lat_i, lon_i] = np.mean(finite_vals)
    
    if doy % 50 == 0:
        print(f"Processed day-of-year {doy}")

print("Thresholds and climatologies computed")

# Set day 60 to mean of days 59 and 61
for ci, (lat_i, lon_i) in enumerate(sea_cells):
    threshold[60, lat_i, lon_i] = (threshold[59, lat_i, lon_i] + threshold[61, lat_i, lon_i]) / 2
    climatology[60, lat_i, lon_i] = (climatology[59, lat_i, lon_i] + climatology[61, lat_i, lon_i]) / 2

print("Day 60 set to mean of days 59 and 61")

# Save intermediate results
np.save('threshold_raw.npy', threshold)
np.save('climatology_raw.npy', climatology)
print("Saved raw thresholds and climatologies")
