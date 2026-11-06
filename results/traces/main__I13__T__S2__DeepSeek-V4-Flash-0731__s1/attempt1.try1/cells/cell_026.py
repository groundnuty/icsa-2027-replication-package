
import numpy as np
import datetime

# Load all data
sst_target = np.load('sst_target.npy')
target_times_int = np.load('target_times.npy')
target_times = target_times_int.astype('datetime64[D]')
thresholds_smooth = np.load('thresholds_smooth.npy')

def date_to_doy(dates):
    month_offsets = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335], dtype=np.int64)
    doys = np.zeros(len(dates), dtype=np.int64)
    for i, d in enumerate(dates):
        dt = np.datetime64(d, 'D').astype(datetime.datetime)
        doys[i] = month_offsets[dt.month - 1] + dt.day
    return doys

target_doy = date_to_doy(target_times)
print("Target doy:", target_doy)

# Sea cells
sea_cells = np.all(np.isfinite(sst_target), axis=0)
n_sea = sea_cells.sum()
print("Number of sea cells:", n_sea)

# For each sea cell, compute hot days
# Get the target period SST for all cells
# sst_target shape: (92, 60, 60)

# For each day, the threshold for each cell is thresholds_smooth[target_doy[t]-1, :, :]
# We need to create a (92, 60, 60) array of thresholds
thresholds_for_target = np.zeros_like(sst_target)
for t in range(len(target_doy)):
    thresholds_for_target[t] = thresholds_smooth[target_doy[t] - 1]

# Hot days: SST >= threshold, for sea cells only
hot = sst_target >= thresholds_for_target
# Land cells should not be hot (they have NaN, so comparison would be False)
# But let's explicitly zero out land cells
hot[~sea_cells] = False

print("Number of hot cell-days:", hot.sum())
print("Hot shape:", hot.shape)

# Save hot for debugging
np.save('hot.npy', hot)
