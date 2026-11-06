
import numpy as np
import datetime

# Load all saved data
sst_base = np.load('sst_base.npy')
sst_target = np.load('sst_target.npy')
base_times_int = np.load('base_times.npy')
target_times_int = np.load('target_times.npy')
base_times = base_times_int.astype('datetime64[D]')
target_times = target_times_int.astype('datetime64[D]')
thresholds_smooth = np.load('thresholds_smooth.npy')
climatologies_smooth = np.load('climatologies_smooth.npy')

print("Shapes:")
print("  sst_target:", sst_target.shape)
print("  thresholds_smooth:", thresholds_smooth.shape)

# Compute doy for target dates
def date_to_doy(dates):
    month_offsets = np.array([0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335], dtype=np.int64)
    doys = np.zeros(len(dates), dtype=np.int64)
    for i, d in enumerate(dates):
        dt = np.datetime64(d, 'D').astype(datetime.datetime)
        doys[i] = month_offsets[dt.month - 1] + dt.day
    return doys

target_doy = date_to_doy(target_times)

# Identify sea cells: cells with finite SST on all target days
sea_cells = np.all(np.isfinite(sst_target), axis=0)  # (60, 60)
print("Number of sea cells:", sea_cells.sum())
print("Sea cell grid:")
print(sea_cells.astype(int))
