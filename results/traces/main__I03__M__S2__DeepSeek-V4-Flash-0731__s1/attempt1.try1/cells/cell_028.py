
import numpy as np

# Load both versions
threshold_old = np.load('/tmp/threshold_smooth.npy')
threshold_new = np.load('/tmp/threshold_smooth_correct.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

# Compare for sea cells
diff = threshold_new - threshold_old
sea_diff = diff[:, sea_cells]
print("Max abs diff:", np.abs(sea_diff).max())
print("Mean abs diff:", np.abs(sea_diff).mean())
print("Num non-zero:", (sea_diff != 0).sum())

# Check for a specific day
target_doy = np.load('/tmp/target_doy.npy')
target_doy_idx = target_doy - 1

old_t = threshold_old[target_doy_idx]
new_t = threshold_new[target_doy_idx]
t_diff = new_t - old_t
sea_t_diff = t_diff[:, sea_cells]
print("Max target threshold diff:", np.abs(sea_t_diff).max())
print("Mean target threshold diff:", np.abs(sea_t_diff).mean())
