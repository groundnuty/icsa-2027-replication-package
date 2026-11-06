
import numpy as np

sea_cells = np.load('/work/sea_cells.npy')
threshold_raw = np.load('/work/threshold_raw.npy')
climatology_raw = np.load('/work/climatology_raw.npy')

sea_idx = np.where(sea_cells)
n_sea = len(sea_idx[0])

# Check raw threshold for all sea cells, all days of year
all_finite_raw = True
for k in range(n_sea):
    i, j = sea_idx[0][k], sea_idx[1][k]
    if not np.all(np.isfinite(threshold_raw[:, i, j])):
        n_nan = np.sum(~np.isfinite(threshold_raw[:, i, j]))
        print(f"Cell ({i},{j}): {n_nan} NaN threshold values out of 366")
        all_finite_raw = False

if all_finite_raw:
    print("All sea cells have finite raw threshold for all 366 days")

# Similarly for climatology
all_finite_raw_clim = True
for k in range(n_sea):
    i, j = sea_idx[0][k], sea_idx[1][k]
    if not np.all(np.isfinite(climatology_raw[:, i, j])):
        n_nan = np.sum(~np.isfinite(climatology_raw[:, i, j]))
        print(f"Cell ({i},{j}): {n_nan} NaN climatology values out of 366")
        all_finite_raw_clim = False

if all_finite_raw_clim:
    print("All sea cells have finite raw climatology for all 366 days")
