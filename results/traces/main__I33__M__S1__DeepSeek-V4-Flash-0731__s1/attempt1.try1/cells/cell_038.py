
import numpy as np

# Verify land cells are 0 in mhw_mask
sea_cells = np.load('output/sea_cells.npy')
mhw_mask = np.load('output/mhw_mask.npy')

# Land cells
land_cells = ~sea_cells
print(f"Land cells: {land_cells.sum()} / {land_cells.size}")

# Check that land cells have all zeros in mhw_mask
land_mhw = mhw_mask[:, land_cells]
print(f"Land cells MHW values: {np.unique(land_mhw)}")
print(f"All land cells are 0 in MHW mask: {np.all(land_mhw == 0)}")

# Check sea cells
sea_mhw = mhw_mask[:, sea_cells]
print(f"Sea cells MHW values: {np.unique(sea_mhw)}")
print(f"Sea cells with MHW: {(sea_mhw.sum(axis=0) > 0).sum()} / {sea_cells.sum()}")

# Check dimensions
print(f"\nmhw_mask shape: {mhw_mask.shape}")
print(f"Expected: (92, 60, 60)")

# Verify threshold values are in kelvin and reasonable
threshold_smooth = np.load('output/threshold_smooth.npy')
print(f"\nThreshold range for sea cells: {np.nanmin(threshold_smooth[:, sea_cells]):.2f} to {np.nanmax(threshold_smooth[:, sea_cells]):.2f} K")

# Verify target SST range
target_sst = np.load('output/target_sst.npy')
sea_sst = target_sst[:, sea_cells]
print(f"Target SST range for sea cells: {np.nanmin(sea_sst):.2f} to {np.nanmax(sea_sst):.2f} K")
