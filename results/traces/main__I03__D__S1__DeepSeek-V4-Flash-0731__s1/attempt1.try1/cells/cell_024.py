
import numpy as np
import pickle

sea_cells = np.load('/work/sea_cells.npy')
print(f"sea_cells shape: {sea_cells.shape}")
print(f"sea_cells[0,0] = {sea_cells[0,0]}")
print(f"Number of sea cells: {np.sum(sea_cells)}")

# Find first sea cell
sea_idx = np.where(sea_cells)
first_k = 0
i, j = sea_idx[0][first_k], sea_idx[1][first_k]
print(f"First sea cell: ({i}, {j}), lat={np.load('/work/lats.npy')[i]}, lon={np.load('/work/lons.npy')[j]}")

threshold = np.load('/work/threshold_raw.npy')
climatology = np.load('/work/climatology_raw.npy')
print(f"threshold shape: {threshold.shape}")

# Check values for first sea cell across some doy
for doy in [1, 59, 60, 61, 153, 244, 366]:
    idx = doy - 1
    print(f"doy={doy}: thr={threshold[idx, i, j]}, clim={climatology[idx, i, j]}")
