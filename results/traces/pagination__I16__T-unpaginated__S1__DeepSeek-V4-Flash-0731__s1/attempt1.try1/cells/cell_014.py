
from datetime import date, timedelta
import numpy as np

# Reload data
all_data = np.load('/tmp/baseline_data.npy')
print('Baseline data shape:', all_data.shape)

# Check which cells are all-NaN across all baseline dates
all_nan_cells = np.all(np.isnan(all_data), axis=0)
print('Cells with all-NaN:', all_nan_cells.sum())
print('Shape:', all_nan_cells.shape)

# Check per cell: how many have any valid data
any_valid = ~np.all(np.isnan(all_data), axis=0)
print('Cells with any valid data:', any_valid.sum())

# Check some specific cells
cell_30_30 = all_data[:, 30, 30]
print(f'Cell (30,30): valid={np.sum(~np.isnan(cell_30_30))}, NaN={np.sum(np.isnan(cell_30_30))}')
