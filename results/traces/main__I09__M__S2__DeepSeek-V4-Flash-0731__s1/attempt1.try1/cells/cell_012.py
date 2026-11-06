
import numpy as np
import pandas as pd

# Load data
sst_data = np.load('/tmp/sst_data.npy')
time_int = np.load('/tmp/time_sub.npy')
time_sub = time_int.astype('datetime64[s]')
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')

# Target period
target_start = np.datetime64('2022-06-01')
target_end = np.datetime64('2022-08-31')
target_mask = (time_sub >= target_start) & (time_sub <= target_end)
target_idx = np.where(target_mask)[0]

# Sea cells: SST finite on every day of target period
target_data = sst_data[target_idx]  # (n_target, n_lat, n_lon)
sea_mask = ~np.isnan(target_data).any(axis=0)  # (n_lat, n_lon)
print("Sea cells:", sea_mask.sum())
print("Sea mask shape:", sea_mask.shape)
print("Total cells:", n_lat * n_lon)
print("Land cells:", n_lat*n_lon - sea_mask.sum())

# Check target period
print("Target days:", len(target_idx))
print("Target DOYs:", [date_to_doy(pd.Timestamp(time_sub[i])) for i in target_idx[:5]], "...", 
      [date_to_doy(pd.Timestamp(time_sub[i])) for i in target_idx[-5:]])

# Save sea mask
np.save('/tmp/sea_mask.npy', sea_mask)
