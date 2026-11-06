
import numpy as np
import datetime as dt

base_data = np.load('/tmp/base_data.npy')
target_data = np.load('/tmp/target_data.npy')
base_times = np.load('/tmp/base_times.npy')
tgt_times = np.load('/tmp/tgt_times.npy')

# Compute day-of-year for all baseline and target dates
base_doy = np.array([day_of_year(t) for t in base_times])
tgt_doy = np.array([day_of_year(t) for t in tgt_times])

print("Baseline DOY range:", base_doy.min(), base_doy.max())
print("Target DOY range:", tgt_doy.min(), tgt_doy.max())

# Identify sea cells: finite SST on every day of the target period
# target_data shape: (92, 60, 60)
sea_mask = np.all(np.isfinite(target_data), axis=0)  # (60, 60)
print("Sea cells count:", sea_mask.sum(), "out of", sea_mask.size)

# Check how many cells have at least some data
has_any = np.any(np.isfinite(target_data), axis=0)
print("Cells with any finite data:", has_any.sum())

# Print the sea mask pattern briefly
print("Sea mask (first 10 rows):")
for i in range(min(10, sea_mask.shape[0])):
    print(''.join(['#' if sea_mask[i,j] else '.' for j in range(sea_mask.shape[1])]))
