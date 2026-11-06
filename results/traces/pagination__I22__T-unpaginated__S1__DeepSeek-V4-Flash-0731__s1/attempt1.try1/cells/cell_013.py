
import numpy as np

# Load raw threshold and climatology
threshold = np.load('cache/threshold_raw.npy')
clim = np.load('cache/clim_raw.npy')

print(f'Shape: {threshold.shape}')
print(f'NaN in threshold: {np.isnan(threshold).sum()}')
print(f'NaN in clim: {np.isnan(clim).sum()}')

# Count cells that are fully NaN (no valid data at all)
# For each cell (i,j), check if all 366 days are NaN
all_nan_cells = np.all(np.isnan(threshold), axis=0)
print(f'Fully NaN cells in threshold: {all_nan_cells.sum()}')
print(f'Total cells: {threshold.shape[1]*threshold.shape[2]}')

# Count cells that have at least one valid value
has_valid = ~all_nan_cells
print(f'Cells with valid data: {has_valid.sum()}')

# Check if any cell has some NaN but some valid
partial = np.any(np.isnan(threshold), axis=0) & ~all_nan_cells
print(f'Cells with partial NaN: {partial.sum()}')

# Print some sample values
print('\nSample threshold values for cell (30,30) across a few days:')
for doy in [1, 59, 60, 61, 100, 152, 153, 154, 200, 300, 366]:
    print(f'  doy {doy}: thresh={threshold[doy-1, 30, 30]:.4f}, clim={clim[doy-1, 30, 30]:.4f}')
