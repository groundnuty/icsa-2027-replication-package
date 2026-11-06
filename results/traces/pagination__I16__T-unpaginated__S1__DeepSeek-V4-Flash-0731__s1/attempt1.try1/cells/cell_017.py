
import numpy as np

thresholds = np.load('/tmp/thresholds.npy')
climatology = np.load('/tmp/climatology.npy')

# Check: for cells that have any valid data, do they have valid thresholds for all days?
thresh_366 = thresholds[1:367]
nan_by_day = np.isnan(thresh_366).sum(axis=0)  # (3600,)
print('Cells with NaN in any day:', np.sum(nan_by_day > 0))
print('Cells with NaN in all days:', np.sum(nan_by_day == 366))

# Check: what's the distribution
non_all_nan = nan_by_day < 366
print('Cells with partial NaN:', np.sum((nan_by_day > 0) & (nan_by_day < 366)))
if np.sum((nan_by_day > 0) & (nan_by_day < 366)) > 0:
    idx = np.where((nan_by_day > 0) & (nan_by_day < 366))[0]
    print('Partial NaN cells at indices:', idx[:10])
    for i in idx[:5]:
        days_with_nan = np.where(np.isnan(thresh_366[:, i]))[0]
        print(f'  Cell {i}: NaN on {len(days_with_nan)} days, first few: {days_with_nan[:5]}')
