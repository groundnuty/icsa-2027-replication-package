
import numpy as np

cell_mhw = np.load('/tmp/cell_mhw.npy')
sea_mask = np.load('/tmp/sea_mask.npy')

# Check if any cell is in an MHW
any_mhw = cell_mhw.any(axis=2)
print(f"Cells in MHW: {any_mhw.sum()}")
print(f"Sea cells: {sea_mask.sum()}")

# Check if any cell-day is in an MHW
print(f"Cell-days in MHW: {cell_mhw.sum()}")

# Verify: all sea cells have no MHW
print(f"All sea cells have no MHW: {not np.any(any_mhw[sea_mask])}")

# Verify: all cell_mhw values are 0 for land cells
print(f"Land cells have no MHW: {not np.any(any_mhw[~sea_mask])}")

# Check the hot day pattern more carefully
hot = np.load('/tmp/hot.npy')
hot_counts = hot.sum(axis=2)
max_consecutive = 0
for i in range(60):
    for j in range(60):
        if not sea_mask[i,j]:
            continue
        h = hot[i,j,:]
        count = 0
        max_count = 0
        for t in range(92):
            if h[t]:
                count += 1
                max_count = max(max_count, count)
            else:
                count = 0
        max_consecutive = max(max_consecutive, max_count)

print(f"Maximum consecutive hot days across all cells: {max_consecutive}")
