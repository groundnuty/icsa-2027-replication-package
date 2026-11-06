
import numpy as np
import pandas as pd

sst_data = np.load('/tmp/sst_data.npy')
times_int = np.load('/tmp/times.npy')
times = pd.to_datetime(times_int, unit='D')

thresholds_smoothed = np.load('/tmp/thresholds_smoothed.npy')
climatology_smoothed = np.load('/tmp/climatology_smoothed.npy')

# Target period indices
times_np = times.values
target_mask = (times_np >= np.datetime64('2015-06-01')) & (times_np <= np.datetime64('2015-08-31'))
target_indices = np.where(target_mask)[0]

# Sea cells
target_sst = sst_data[target_indices, :, :]
finite_all = np.all(np.isfinite(target_sst), axis=0)
sea_cells = np.argwhere(finite_all)
print("Number of sea cells:", len(sea_cells))

# Compute doy for target days
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

target_doy = np.array([compute_doy(times[i].month, times[i].day) for i in target_indices])

# Check NaN in smoothed thresholds for sea cells at target days
nan_count = 0
for d in target_doy:
    for lat, lon in sea_cells:
        if np.isnan(thresholds_smoothed[d-1, lat, lon]):
            nan_count += 1
print("NaN count in smoothed thresholds for sea cells at target days:", nan_count)

# Check NaN in smoothed climatology
nan_count2 = 0
for d in target_doy:
    for lat, lon in sea_cells:
        if np.isnan(climatology_smoothed[d-1, lat, lon]):
            nan_count2 += 1
print("NaN count in smoothed climatology for sea cells at target days:", nan_count2)
