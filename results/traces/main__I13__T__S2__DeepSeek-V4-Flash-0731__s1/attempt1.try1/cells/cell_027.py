
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

# Sea cells
sea_cells = np.all(np.isfinite(sst_target), axis=0)  # (60, 60)
n_sea = sea_cells.sum()
print("Number of sea cells:", n_sea)

# For each day, the threshold for each cell is thresholds_smooth[target_doy[t]-1, :, :]
thresholds_for_target = np.zeros_like(sst_target)
for t in range(len(target_doy)):
    thresholds_for_target[t] = thresholds_smooth[target_doy[t] - 1]

# Hot days: SST >= threshold
hot = sst_target >= thresholds_for_target
# Land cells should not be hot
hot = hot & sea_cells[np.newaxis, :, :]

print("Number of hot cell-days:", hot.sum())
print("Hot shape:", hot.shape)

# Count hot days per cell
hot_per_cell = hot.sum(axis=0)
print("Hot days per cell (unique values):", np.unique(hot_per_cell[sea_cells]))

np.save('hot.npy', hot)
