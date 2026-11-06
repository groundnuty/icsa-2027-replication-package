
import numpy as np

sea_mask = np.load('sea_mask.npy')
threshold_smooth = np.load('threshold_smooth.npy')
climatology_smooth = np.load('climatology_smooth.npy')

sea_cells = np.argwhere(sea_mask)
n_nan_threshold = 0
n_nan_clim = 0
for ci, (lat_i, lon_i) in enumerate(sea_cells):
    if np.isnan(threshold_smooth[:, lat_i, lon_i]).any():
        n_nan_threshold += 1
    if np.isnan(climatology_smooth[:, lat_i, lon_i]).any():
        n_nan_clim += 1

print(f"Sea cells with NaN in threshold: {n_nan_threshold}")
print(f"Sea cells with NaN in climatology: {n_nan_clim}")

# Check land cells for reference
land_cells = np.argwhere(~sea_mask)
n_land_threshold = 0
for ci, (lat_i, lon_i) in enumerate(land_cells):
    if np.isnan(threshold_smooth[:, lat_i, lon_i]).any():
        n_land_threshold += 1
print(f"Land cells with any NaN in threshold: {n_land_threshold}/{len(land_cells)}")
