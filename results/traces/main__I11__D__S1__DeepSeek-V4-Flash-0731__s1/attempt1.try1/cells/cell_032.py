
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Load data
smooth_thresholds = np.load('/work/smooth_thresholds.npy')
target_sst = np.load('/work/target_sst.npy')
sea_mask = np.load('/work/sea_mask.npy')
hot = np.load('/work/hot.npy')
mhw_mask = np.load('/work/mhw_mask.npy')

import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time_vals = ds.time.values
target_idx = np.where((time_vals >= np.datetime64('2021-06-01')) & (time_vals <= np.datetime64('2021-08-31')))[0]
target_time = time_vals[target_idx]
target_dates = [pd.Timestamp(t).date() for t in target_time]

def day_of_year_366(d):
    m, day = d.month, d.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[:m-1]) + day

target_doy = np.array([day_of_year_366(d) for d in target_dates])

# Check cell (30, 30)
i, j = 30, 30
print(f"Cell ({i},{j}): sea={sea_mask[i,j]}")
if sea_mask[i,j]:
    # Print SST, threshold, and hot status for the first 20 days
    print("Day | Date       | SST      | Threshold | Hot | MHW")
    print("-" * 60)
    for t in range(min(20, len(target_dates))):
        sst = target_sst[t, i, j]
        thresh = smooth_thresholds[target_doy[t]-1, i, j]
        is_hot = hot[t, i, j]
        is_mhw = mhw_mask[t, i, j]
        print(f"{t:3d} | {target_dates[t]} | {sst:8.3f} | {thresh:9.3f} | {'Y' if is_hot else 'N':3s} | {is_mhw}")

# Check another cell
i2, j2 = 0, 0
print(f"\nCell ({i2},{j2}): sea={sea_mask[i2,j2]}")
if sea_mask[i2,j2]:
    print("Day | Date       | SST      | Threshold | Hot | MHW")
    print("-" * 60)
    for t in range(min(20, len(target_dates))):
        sst = target_sst[t, i2, j2]
        thresh = smooth_thresholds[target_doy[t]-1, i2, j2]
        is_hot = hot[t, i2, j2]
        is_mhw = mhw_mask[t, i2, j2]
        print(f"{t:3d} | {target_dates[t]} | {sst:8.3f} | {thresh:9.3f} | {'Y' if is_hot else 'N':3s} | {is_mhw}")
