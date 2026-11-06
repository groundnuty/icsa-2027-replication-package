
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Load data
smooth_thresholds = np.load('/work/smooth_thresholds.npy')  # (366, 60, 60)
smooth_climatology = np.load('/work/smooth_climatology.npy')
sea_mask = np.load('/work/sea_mask.npy')
target_sst = np.load('/work/target_sst.npy')  # (92, 60, 60)

# Reload time data
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time_vals = ds.time.values
target_idx = np.where((time_vals >= np.datetime64('2021-06-01')) & (time_vals <= np.datetime64('2021-08-31')))[0]
target_time = time_vals[target_idx]
target_dates = [pd.Timestamp(t).date() for t in target_time]

# Day of year mapping
def day_of_year_366(d):
    m, day = d.month, d.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[:m-1]) + day

target_doy = np.array([day_of_year_366(d) for d in target_dates])
print(f"Target DOYs: {target_doy}")

# For each cell, check if each target day is hot
# hot[time, i, j] = 1 if SST >= threshold, 0 otherwise
n_time = len(target_dates)
n_lat, n_lon = 60, 60

# Extract the threshold for each target day
target_thresholds = smooth_thresholds[target_doy - 1]  # (92, 60, 60)

# Check if each day is hot
hot = np.zeros((n_time, n_lat, n_lon), dtype=bool)
for t in range(n_time):
    for i in range(n_lat):
        for j in range(n_lon):
            if sea_mask[i, j]:
                sst = target_sst[t, i, j]
                if not np.isnan(sst):
                    thresh = target_thresholds[t, i, j]
                    if not np.isnan(thresh):
                        hot[t, i, j] = (sst >= thresh)

print(f"Hot cells per day: {hot.sum(axis=(1,2))}")
print(f"Total hot cell-days: {hot.sum()}")
