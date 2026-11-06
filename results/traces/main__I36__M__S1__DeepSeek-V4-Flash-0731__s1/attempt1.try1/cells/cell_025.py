
import numpy as np

# Check for infinite values in target data
target_data = np.load('/tmp/target_data.npy')
print(f"Infinite values in target data: {np.isinf(target_data).sum()}")
print(f"NaN values in target data: {np.isnan(target_data).sum()}")

# Check sea cells more carefully
sea_cells_nan = ~np.isnan(target_data).any(axis=0)
sea_cells_finite = np.isfinite(target_data).all(axis=0)
print(f"Sea cells (not NaN on all days): {sea_cells_nan.sum()}")
print(f"Sea cells (finite on all days): {sea_cells_finite.sum()}")
print(f"Difference: {(sea_cells_nan != sea_cells_finite).sum()}")

# If no infinite values, they're the same
if np.isinf(target_data).sum() == 0:
    print("No infinite values, so sea cells are the same either way")
