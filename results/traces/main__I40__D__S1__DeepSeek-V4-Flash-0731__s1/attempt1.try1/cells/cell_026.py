
import numpy as np
import pandas as pd

# Load data
target_sst = np.load('/work/target_sst.npy')
thresholds = np.load('/work/thresholds.npy')
climatology = np.load('/work/climatology.npy')

n_lat, n_lon = target_sst.shape[1], target_sst.shape[2]

# Sea cells
sea_cells = np.zeros((n_lat, n_lon), dtype=bool)
for i in range(n_lat):
    for j in range(n_lon):
        if np.all(np.isfinite(target_sst[:, i, j])):
            sea_cells[i, j] = True

# Check if sea cells have NaN in thresholds or climatology
sea_with_nan_thr = 0
sea_with_nan_clim = 0
for i in range(n_lat):
    for j in range(n_lon):
        if sea_cells[i, j]:
            if np.isnan(thresholds[:, i, j]).any():
                sea_with_nan_thr += 1
                # Find which doys are NaN
                nan_doy = np.where(np.isnan(thresholds[:, i, j]))[0] + 1
                if sea_with_nan_thr <= 3:
                    print(f"  Sea cell ({i},{j}) has NaN threshold at doys: {nan_doy[:20]}...")
            if np.isnan(climatology[:, i, j]).any():
                sea_with_nan_clim += 1

print(f"Sea cells with NaN in threshold: {sea_with_nan_thr}")
print(f"Sea cells with NaN in climatology: {sea_with_nan_clim}")

# Also check: how many of the 366 doys have valid thresholds for each sea cell?
min_valid = 366
for i in range(n_lat):
    for j in range(n_lon):
        if sea_cells[i, j]:
            n_valid = np.sum(~np.isnan(thresholds[:, i, j]))
            min_valid = min(min_valid, n_valid)
print(f"Minimum number of valid threshold days for sea cells: {min_valid}")

# Check which cells are NOT sea cells
print(f"\nNon-sea cells (land): {3600 - sea_cells.sum()}")
# Sample some non-sea cells
non_sea = ~sea_cells
idx = np.where(non_sea)
for k in range(min(5, len(idx[0]))):
    i, j = idx[0][k], idx[1][k]
    nan_count = np.sum(np.isnan(target_sst[:, i, j]))
    print(f"  Non-sea cell ({i},{j}): {nan_count} NaN out of 92 target days")
