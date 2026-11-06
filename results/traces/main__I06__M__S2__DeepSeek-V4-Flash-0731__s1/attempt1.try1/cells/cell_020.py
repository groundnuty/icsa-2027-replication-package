
import numpy as np

threshold_raw = np.load('/tmp/threshold_raw.npy')
clim_raw = np.load('/tmp/clim_raw.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

# For first sea cell, check NaN pattern
sea_idx = np.where(sea_cells)
i, j = sea_idx[0][0], sea_idx[1][0]

nonnan_doy_thr = np.where(~np.isnan(threshold_raw[1:367, i, j]))[0] + 1
print(f"Cell ({i},{j}): {len(nonnan_doy_thr)} non-NaN doy values out of 366")
print("Non-NaN doy:", nonnan_doy_thr)

# Check which cells have all-NaN for specific doys
for d in [1, 60, 100, 153, 200, 244, 300, 366]:
    n_nan = np.isnan(threshold_raw[d]).sum()
    n_sea_nan = np.isnan(threshold_raw[d])[sea_cells].sum()
    print(f"doy {d}: {n_nan} NaN total, {n_sea_nan} NaN sea cells")
