
import numpy as np
import pandas as pd

# Load saved data
sst_data = np.load('/tmp/sst_data.npy')
time_int = np.load('/tmp/time_sub.npy')
time_sub = time_int.astype('datetime64[s]')
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')

print("sst_data shape:", sst_data.shape)
print("time_sub range:", time_sub[0], "to", time_sub[-1])

# Define DOY function
def date_to_doy(date):
    ts = pd.Timestamp(date)
    month, day = ts.month, ts.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month-1] + day

# Compute DOY for each time step
doy_array = np.array([date_to_doy(d) for d in pd.to_datetime(time_sub)])

# Check target period indices
target_start = np.datetime64('2022-06-01')
target_end = np.datetime64('2022-08-31')
target_mask = (time_sub >= target_start) & (time_sub <= target_end)
target_idx = np.where(target_mask)[0]
print("Target period indices:", target_idx[0], "to", target_idx[-1], "count:", len(target_idx))
print("Target period DOYs:", doy_array[target_idx[0]], "to", doy_array[target_idx[-1]])

# Baseline period
baseline_start = np.datetime64('1992-01-01')
baseline_end = np.datetime64('2002-12-31')
baseline_mask = (time_sub >= baseline_start) & (time_sub <= baseline_end)
baseline_idx = np.where(baseline_mask)[0]
print("Baseline indices:", baseline_idx[0], "to", baseline_idx[-1], "count:", len(baseline_idx))
