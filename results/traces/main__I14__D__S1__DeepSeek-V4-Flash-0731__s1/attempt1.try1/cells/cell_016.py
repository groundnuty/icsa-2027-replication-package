
import numpy as np

# Load target data
target_sst = np.load('/work/target_sst.npy')

# Sea cells: cells where SST is finite on every day of the target period
# target_sst shape: (92, 60, 60)
n_time, n_lat, n_lon = target_sst.shape

# Check if finite on every day
sea_cells = np.all(np.isfinite(target_sst), axis=0)
print(f"Sea cells: {sea_cells.sum()} out of {n_lat * n_lon}")

# Show which cells are sea vs land
print(f"Sea cell fraction: {sea_cells.mean():.4f}")

# Check a few cells
print(f"First 10 sea cells (lat, lon):")
count = 0
for i in range(n_lat):
    for j in range(n_lon):
        if sea_cells[i, j]:
            print(f"  ({i}, {j})")
            count += 1
            if count >= 5:
                break
    if count >= 5:
        break
