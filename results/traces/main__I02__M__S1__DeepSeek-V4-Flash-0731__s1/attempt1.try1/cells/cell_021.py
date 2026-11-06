
import numpy as np

threshold = np.load('/tmp/threshold_unsmoothed.npy')
target_data = np.load('/tmp/target_data.npy')
sea_mask = np.all(np.isfinite(target_data), axis=0)

# Check if any sea cell has NaN in threshold
sea_nan_count = np.isnan(threshold[sea_mask]).sum()
print(f"NaN values in threshold for sea cells: {sea_nan_count}")
total_sea_vals = sea_mask.sum() * 366
print(f"Total values for sea cells: {total_sea_vals}")
print(f"NaN percentage: {sea_nan_count / total_sea_vals * 100:.2f}%")

# Find which sea cells have NaN
nan_cells = []
for i in range(60):
    for j in range(60):
        if sea_mask[i,j] and np.isnan(threshold[i,j,:]).any():
            nan_doys = np.where(np.isnan(threshold[i,j,:]))[0]
            nan_cells.append((i,j,nan_doys))
            
print(f"Sea cells with NaN in threshold: {len(nan_cells)}")
for i,j,doys in nan_cells[:10]:
    print(f"  Cell ({i},{j}): NaN at DOYs {doys}")
