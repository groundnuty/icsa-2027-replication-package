import numpy as np
import pickle

# Load per_cell_mhw and sea_cells
per_cell_mhw = np.load('/tmp/work/per_cell_mhw.npy')
sea_cells = np.load('/tmp/work/sea_cells.npy')

print(f"per_cell_mhw shape: {per_cell_mhw.shape}")
print(f"per_cell_mhw dtype: {per_cell_mhw.dtype}")
print(f"per_cell_mhw values: {np.unique(per_cell_mhw)}")

# Verify land cells are all 0
land_cells = ~sea_cells
land_mhw = per_cell_mhw[:, land_cells]
print(f"Land cells in MHW: {land_mhw.sum()}")
print(f"All land cells are 0: {np.all(land_mhw == 0)}")

# Verify sea cells can be 0 or 1
sea_mhw = per_cell_mhw[:, sea_cells]
print(f"Sea cell MHW values: {np.unique(sea_mhw)}")

# Check the shape of the output mask
print(f"Final mhw shape: {per_cell_mhw.shape}")

# Verify time dimension
print(f"Time steps: {per_cell_mhw.shape[0]} (target days)")

# Verify lat/lon dimensions
print(f"Lat steps: {per_cell_mhw.shape[1]}")
print(f"Lon steps: {per_cell_mhw.shape[2]}")
