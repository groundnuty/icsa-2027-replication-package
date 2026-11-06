
from datetime import date, timedelta
import numpy as np

# Load data
target_data = np.load('/tmp/target_data.npy')  # (92, 60, 60)
thresh_smooth = np.load('/tmp/thresh_smooth.npy')  # (366, 3600)
clim_smooth = np.load('/tmp/clim_smooth.npy')  # (366, 3600)

print('Target data shape:', target_data.shape)
print('Threshold shape:', thresh_smooth.shape)

# Day-of-year function
month_starts = [1, 32, 61, 92, 122, 153, 183, 214, 245, 275, 306, 336]
def doy(dt):
    return month_starts[dt.month - 1] + dt.day - 1

# Target dates
target_start = date(2008, 6, 1)
target_end = date(2008, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)

target_doys = np.array([doy(dt) for dt in target_dates])
print('Target day-of-years:', target_doys)

# Reshape target data to (92, 3600)
target_flat = target_data.reshape(92, -1)  # (92, 3600)
print('Target flat shape:', target_flat.shape)

# Get thresholds for target days: (92, 3600)
target_thresholds = thresh_smooth[target_doys - 1]  # (92, 3600)
print('Target thresholds shape:', target_thresholds.shape)

# Determine sea cells: cells with finite SST on every target day
sea_cells = ~np.any(np.isnan(target_flat), axis=0)  # (3600,)
print('Sea cells:', sea_cells.sum(), 'out of', 3600)

# Compute hot days for sea cells
# hot[t, c] = target_flat[t, c] >= target_thresholds[t, c] for sea cells
hot = np.zeros_like(target_flat, dtype=bool)
for c in range(3600):
    if sea_cells[c]:
        for t in range(92):
            if not np.isnan(target_flat[t, c]) and not np.isnan(target_thresholds[t, c]):
                hot[t, c] = target_flat[t, c] >= target_thresholds[t, c]

print('Number of hot cell-days:', hot.sum())

# Save intermediate
np.save('/tmp/hot.npy', hot)
np.save('/tmp/sea_cells.npy', sea_cells)
print('Saved hot and sea_cells')
