
import xarray as xr
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Reload the original data from the netcdf
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat_idx = np.arange(109, 169)
lon_idx = np.arange(373, 433)

time_vals = ds.time.values

baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
baseline_mask = (time_vals >= baseline_start) & (time_vals <= baseline_end)
baseline_idx = np.where(baseline_mask)[0]

target_start = np.datetime64('2021-06-01')
target_end = np.datetime64('2021-08-31')
target_mask = (time_vals >= target_start) & (time_vals <= target_end)
target_idx = np.where(target_mask)[0]

baseline_time = time_vals[baseline_idx]
target_time = time_vals[target_idx]

# Convert to Python dates
baseline_dates = [pd.Timestamp(t).date() for t in baseline_time]
target_dates = [pd.Timestamp(t).date() for t in target_time]

print(f"Baseline dates: {baseline_dates[0]} to {baseline_dates[-1]}, count: {len(baseline_dates)}")
print(f"Target dates: {target_dates[0]} to {target_dates[-1]}, count: {len(target_dates)}")

# Day of year mapping function (1-366)
def day_of_year_366(d):
    m, day = d.month, d.day
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return sum(days_in_month[:m-1]) + day

# Compute day of year for each baseline and target date
baseline_doy = np.array([day_of_year_366(d) for d in baseline_dates])
target_doy = np.array([day_of_year_366(d) for d in target_dates])

print(f"Baseline DOY range: {baseline_doy.min()} to {baseline_doy.max()}")
print(f"Target DOY range: {target_doy.min()} to {target_doy.max()}")

# Verify some DOY values
for i in [0, 1, 30, 58, 59, 60]:
    if i < len(baseline_dates):
        print(f"  Baseline date {baseline_dates[i]}: DOY = {baseline_doy[i]}")
