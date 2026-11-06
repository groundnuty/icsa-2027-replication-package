
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Load saved data
baseline_sst = np.load('/work/baseline_sst.npy')
target_sst = np.load('/work/target_sst.npy')
lat_vals = np.load('/work/lat_vals.npy')
lon_vals = np.load('/work/lon_vals.npy')

# We need to reconstruct the time arrays
# Let me reload from the dataset to get proper dates
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time_vals = ds.time.values

baseline_idx = np.where((time_vals >= np.datetime64('1991-12-27')) & (time_vals <= np.datetime64('2003-01-05')))[0]
target_idx = np.where((time_vals >= np.datetime64('2021-06-01')) & (time_vals <= np.datetime64('2021-08-31')))[0]

baseline_time = time_vals[baseline_idx]
target_time = time_vals[target_idx]

baseline_dates = [pd.Timestamp(t).date() for t in baseline_time]
target_dates = [pd.Timestamp(t).date() for t in target_time]

print(f"Baseline: {baseline_dates[0]} to {baseline_dates[-1]}, n={len(baseline_dates)}")
print(f"Target: {target_dates[0]} to {target_dates[-1]}, n={len(target_dates)}")

# Day of year mapping (always Feb=29)
def day_of_year_366(d):
    m, day = d.month, d.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[:m-1]) + day

# Build mapping from date to index in baseline_sst
baseline_date_to_idx = {}
for i, d in enumerate(baseline_dates):
    baseline_date_to_idx[d] = i

# Identify sea cells: finite on every target day
sea_mask = np.all(~np.isnan(target_sst), axis=0)  # (60, 60)
n_sea = np.sum(sea_mask)
print(f"Sea cells: {n_sea}")

# For each day-of-year d (1-366, d≠60), build the pool of SST values
# First, let me figure out which baseline dates correspond to each day-of-year
# and their ±5 day windows

# For each day-of-year d, find the (month, day)
days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
month_day_for_doy = {}
for m in range(12):
    for day in range(1, days_in_month[m] + 1):
        doy = sum(days_in_month[:m]) + day
        if doy not in month_day_for_doy:
            month_day_for_doy[doy] = (m + 1, day)

# Verify some
print(f"DOY 1: {month_day_for_doy[1]}")
print(f"DOY 59: {month_day_for_doy[59]}")
print(f"DOY 60: {month_day_for_doy[60]}")
print(f"DOY 61: {month_day_for_doy[61]}")
print(f"DOY 153: {month_day_for_doy[153]}")
print(f"DOY 244: {month_day_for_doy[244]}")
print(f"DOY 366: {month_day_for_doy[366]}")
