
import numpy as np
import pandas as pd

# Load
sst_data = np.load('/tmp/sst_data.npy')
times_int = np.load('/tmp/times.npy')
times = pd.to_datetime(times_int, unit='D')
thresholds_smoothed = np.load('/tmp/thresholds_smoothed.npy')
mhw_mask = np.load('/tmp/mhw_mask.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
target_indices = np.load('/tmp/target_indices.npy')

def compute_doy(month, day):
    if month == 1:
        return day
    elif month == 2:
        return 31 + day
    else:
        days_before = 60
        days_in_month = {3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}
        for m in range(3, month):
            days_before += days_in_month[m]
        return days_before + day

times_np = times.values
target_mask = (times_np >= np.datetime64('2015-06-01')) & (times_np <= np.datetime64('2015-08-31'))
target_indices = np.where(target_mask)[0]

target_doy = np.array([compute_doy(times[i].month, times[i].day) for i in target_indices])

# Let's examine a sea cell with some MHW activity
active_per_cell = mhw_mask.sum(axis=1)
cells_with_mhw = np.where(active_per_cell > 0)[0]
print("Cells with MHW:", len(cells_with_mhw))

for ci in cells_with_mhw[:5]:
    lat, lon = sea_cells[ci]
    print(f"\nCell ({lat},{lon}):")
    print(f"  MHW mask: {mhw_mask[ci, :]}")
    sst_vals = sst_data[target_indices, lat, lon]
    thresh_vals = thresholds_smoothed[target_doy - 1, lat, lon]
    hot_days = sst_vals >= thresh_vals
    print(f"  Hot days: {hot_days.astype(int)}")
    print(f"  SST: {sst_vals}")
    print(f"  Threshold: {thresh_vals}")
