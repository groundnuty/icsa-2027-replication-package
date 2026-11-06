
import numpy as np

threshold = np.load('threshold_raw.npy')
climatology = np.load('climatology_raw.npy')

# Check NaN patterns
thr_nan = np.isnan(threshold)
print('Threshold NaN fraction overall:', thr_nan[1:367].mean())
# Per cell, how many DOYs are NaN
cell_nan_count = thr_nan[1:367].sum(axis=0)
print('Per-cell NaN count distribution: min={}, max={}, mean={:.2f}'.format(
    cell_nan_count.min(), cell_nan_count.max(), cell_nan_count.mean()))
# Which cells have 0 NaN
no_nan_cells = (cell_nan_count == 0).sum()
print('Cells with no NaN in threshold:', no_nan_cells)
# Which cells have some but not all NaN
partial = ((cell_nan_count > 0) & (cell_nan_count < 366)).sum()
all_nan = (cell_nan_count == 366).sum()
print('Partial NaN cells:', partial, 'All NaN cells:', all_nan)
