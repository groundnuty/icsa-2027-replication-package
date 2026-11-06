
import numpy as np

threshold_raw = np.load('/tmp/threshold_raw.npy')

# For each cell, check how many days of year have NaN threshold
n_doy = 366
n_lat, n_lon = 60, 60

nan_per_cell = np.isnan(threshold_raw).sum(axis=0)
print("NaN per cell (doy dim):")
print("  min:", nan_per_cell.min())
print("  max:", nan_per_cell.max())
print("  mean:", nan_per_cell.mean())

# Which cells have 0 NaN (all days valid)?
cells_all_valid = np.sum(nan_per_cell == 0)
print("Cells with all 366 days valid:", cells_all_valid)
print("Cells with all 366 days NaN:", np.sum(nan_per_cell == 366))

# Check cells with some NaN
partial = (nan_per_cell > 0) & (nan_per_cell < 366)
print("Cells with partial NaN:", partial.sum())

# Let's look at the NaN pattern for a specific cell
# First check which cells have NaN
nan_rows, nan_cols = np.where(nan_per_cell > 0)
print("Sample cells with NaN:", list(zip(nan_rows[:10], nan_cols[:10])))
