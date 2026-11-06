
import numpy as np

target_data = np.load('/tmp/target_data.npy')
# Sea cells: SST finite on every target day
sea_mask = np.all(np.isfinite(target_data), axis=0)
print(f"Sea cells: {sea_mask.sum()}")
print(f"Land cells: {sea_mask.size - sea_mask.sum()}")

# Check if sea_mask matches cells without NaN in threshold
threshold = np.load('/tmp/threshold_unsmoothed.npy')

# For each cell, check if it has any finite value in threshold
has_threshold = ~np.all(np.isnan(threshold), axis=2)
print(f"Cells with at least one finite threshold: {has_threshold.sum()}")
print(f"Sea cells: {sea_mask.sum()}")

# Check agreement
print(f"Agreement (sea == has_threshold): {np.array_equal(sea_mask, has_threshold)}")
