
import numpy as np

threshold_smooth = np.load('/tmp/threshold_smooth_correct.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

# Check NaN pattern
nan_mask = np.isnan(threshold_smooth)
# For each cell, check if any NaN across days
nan_by_cell = nan_mask.any(axis=0)
print("Cells with any NaN in smoothed threshold:", nan_by_cell.sum())
print("These should match non-sea cells:", (60*60 - sea_cells.sum()))

# Verify all sea cells have no NaN
sea_nan = nan_by_cell & sea_cells
print("Sea cells with NaN:", sea_nan.sum())

# Land cells with no NaN
land_no_nan = (~nan_by_cell) & (~sea_cells)
print("Land cells with no NaN:", land_no_nan.sum())
