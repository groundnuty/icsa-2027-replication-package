
import numpy as np
import pandas as pd

# Load data
sst_data = np.load('/tmp/sst_data.npy')
time_int = np.load('/tmp/time_sub.npy')
time_sub = time_int.astype('datetime64[s]')
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')

n_lat, n_lon = sst_data.shape[1], sst_data.shape[2]

def date_to_doy(date):
    ts = pd.Timestamp(date)
    month, day = ts.month, ts.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month-1] + day

# Target period
target_start = np.datetime64('2022-06-01')
target_end = np.datetime64('2022-08-31')
target_mask = (time_sub >= target_start) & (time_sub <= target_end)
target_idx = np.where(target_mask)[0]

# Sea cells
target_data = sst_data[target_idx]
sea_mask = ~np.isnan(target_data).any(axis=0)
print("Sea cells:", sea_mask.sum())
print("Total cells:", n_lat * n_lon)
print("Land cells:", n_lat*n_lon - sea_mask.sum())

np.save('/tmp/sea_mask.npy', sea_mask)

# Check target DOYs
for i in [target_idx[0], target_idx[30], target_idx[60], target_idx[-1]]:
    print(f"Time {time_sub[i]}: DOY {date_to_doy(pd.Timestamp(time_sub[i]))}")
