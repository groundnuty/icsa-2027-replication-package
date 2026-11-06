
import numpy as np

# Load intermediate results
threshold_smooth = np.load('/tmp/threshold_smooth.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
target_sst = np.load('/tmp/target_sst.npy')
target_doy = np.load('/tmp/target_doy.npy')

# target_doy are 1-indexed (1-366), convert to 0-indexed (0-365) for threshold lookup
target_doy_idx = target_doy - 1
print("Target doy idx:", target_doy_idx[0], "to", target_doy_idx[-1])

# Get thresholds for each target day and cell
# threshold_smooth shape: (366, 60, 60)
# For each target day i, threshold_smooth[target_doy_idx[i]] gives (60, 60)
thresh_for_target = threshold_smooth[target_doy_idx]  # (92, 60, 60)
print("Threshold for target shape:", thresh_for_target.shape)

# Determine hot days: SST >= threshold
# target_sst in float32, convert to float64
target_sst64 = target_sst.astype(np.float64)
hot = target_sst64 >= thresh_for_target
print("Hot days count:", hot.sum(), "of", hot.size)
print("Hot days per cell distribution:")
hot_by_cell = hot.sum(axis=0)
print("Hot cells (some hot days):", (hot_by_cell > 0).sum())
print("Cells with >=5 hot days:", (hot_by_cell >= 5).sum())

# Check: only sea cells should be considered. Land cells should be not hot.
# Ensure land cells are not hot
hot[~sea_cells] = False
print("Hot days (sea only):", hot.sum())
