
import numpy as np

baseline_sst = np.load('baseline_sst.npy')
sea_mask = np.load('sea_mask.npy')

# Check cell (0,0)
cell_data = baseline_sst[:, 0, 0]
finite_count = np.sum(np.isfinite(cell_data))
total = len(cell_data)
print(f"Cell (0,0): {finite_count}/{total} finite in baseline")

# Check some other land cells
land_cells = np.argwhere(~sea_mask)
for i in range(min(5, len(land_cells))):
    lat_i, lon_i = land_cells[i]
    cell_data = baseline_sst[:, lat_i, lon_i]
    finite_count = np.sum(np.isfinite(cell_data))
    print(f"Land cell ({lat_i}, {lon_i}): {finite_count}/{total} finite in baseline")

# Also check if any sea cell has NaN in baseline
sea_cells = np.argwhere(sea_mask)
for i in range(min(5, len(sea_cells))):
    lat_i, lon_i = sea_cells[i]
    cell_data = baseline_sst[:, lat_i, lon_i]
    finite_count = np.sum(np.isfinite(cell_data))
    print(f"Sea cell ({lat_i}, {lon_i}): {finite_count}/{total} finite in baseline")
