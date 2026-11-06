
import numpy as np

per_cell_mhw = np.load('/tmp/per_cell_mhw.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

# Check: non-sea cells should have 0 in per_cell_mhw
non_sea = ~sea_cells
non_sea_mhw = per_cell_mhw[:, non_sea]
print(f"Non-sea cells MHW count: {non_sea_mhw.sum()}")

# Check: sea cells should have correct values
print(f"per_cell_mhw shape: {per_cell_mhw.shape}")
print(f"per_cell_mhw sum: {per_cell_mhw.sum()}")
print(f"per_cell_mhw max: {per_cell_mhw.max()}")

# Verify dims
print(f"Target days: {per_cell_mhw.shape[0]}")
print(f"Lat: {per_cell_mhw.shape[1]}")
print(f"Lon: {per_cell_mhw.shape[2]}")
