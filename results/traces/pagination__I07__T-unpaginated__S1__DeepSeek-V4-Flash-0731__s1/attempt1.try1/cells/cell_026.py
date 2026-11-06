
import numpy as np

# Load data
threshold_smooth_v2 = np.load('/tmp/threshold_smooth_v2.npy')  # float64
sea_cells = np.load('/tmp/sea_cells.npy')

print(f"Threshold shape: {threshold_smooth_v2.shape}")
print(f"NaN count total: {np.isnan(threshold_smooth_v2).sum()}")

# Check NaN for sea cells
sea_idx = np.where(sea_cells)
sea_nan = np.zeros(threshold_smooth_v2.shape[0], dtype=bool)
for si in range(len(sea_idx[0])):
    li, loi = sea_idx[0][si], sea_idx[1][si]
    cell_vals = threshold_smooth_v2[:, li, loi]
    if np.isnan(cell_vals).any():
        print(f"Sea cell ({li},{loi}) has {np.isnan(cell_vals).sum()} NaN in threshold")
        sea_nan |= np.isnan(cell_vals)

print(f"Sea cells with NaN in threshold: {sea_nan.sum() if sea_nan.any() else 0}")

# Check NaN for non-sea cells
non_sea = ~sea_cells
non_sea_nan = np.isnan(threshold_smooth_v2).any(axis=0) & non_sea
print(f"Non-sea cells with NaN in threshold: {non_sea_nan.sum()}")

# Check: are all NaN values from non-sea cells?
all_nan_mask = np.isnan(threshold_smooth_v2).any(axis=0)
print(f"Total cells with any NaN in threshold: {all_nan_mask.sum()}")
print(f"Non-sea cells with any NaN: {(all_nan_mask & non_sea).sum()}")
print(f"Sea cells with any NaN: {(all_nan_mask & sea_cells).sum()}")
