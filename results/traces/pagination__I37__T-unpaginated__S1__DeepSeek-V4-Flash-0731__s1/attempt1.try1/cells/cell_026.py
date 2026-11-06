
import numpy as np
import datetime

# Load data
target_sst = np.load('work/target_sst.npy')
sea_mask = np.load('work/sea_mask.npy')
threshold_smooth = np.load('work/threshold_smooth.npy')

# Day of year mapping
def doy_from_date(date):
    month_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days[date.month-1] + date.day

# Target dates
target_start = datetime.date(2012, 6, 1)
target_end = datetime.date(2012, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += datetime.timedelta(days=1)

target_doy = np.array([doy_from_date(date) for date in target_dates])

n_target = len(target_dates)
n_lat, n_lon = 60, 60

threshold_3d = threshold_smooth.reshape(366, n_lat, n_lon)
threshold_for_target = threshold_3d[target_doy - 1]

hot = (target_sst >= threshold_for_target) & sea_mask[np.newaxis, :, :]

# Find hot cell-days
hot_indices = np.where(hot)
print(f"Number of hot cell-days: {len(hot_indices[0])}")
for t, i, j in zip(hot_indices[0], hot_indices[1], hot_indices[2]):
    date = target_dates[t]
    doy = target_doy[t]
    sst = target_sst[t, i, j]
    thr = threshold_3d[doy-1, i, j]
    print(f"  {date} doy={doy}, cell=({i},{j}): sst={sst:.4f}, thr={thr:.4f}, diff={sst-thr:.4f}")
