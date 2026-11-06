
import xarray as xr
import numpy as np
import datetime

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Load data
base_data = ds['analysed_sst'].isel(time=slice(3647, 7675), latitude=slice(260, 320), longitude=slice(485, 545)).load()
target_data = ds['analysed_sst'].isel(time=slice(12935, 13027), latitude=slice(260, 320), longitude=slice(485, 545)).load()

print("Base data shape:", base_data.shape)
print("Target data shape:", target_data.shape)
print("Base time range:", base_data.time.values[0], "to", base_data.time.values[-1])

# Get time values as datetime
base_times = base_data.time.values
target_times = target_data.time.values

# Day of year mapping function
def doy_from_datetime64(t):
    dt = pd.Timestamp(t).to_pydatetime()
    year = dt.year
    month = dt.month
    day = dt.day
    # Check leap year
    is_leap = (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0))
    # Standard day of year (1-based)
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if is_leap:
        days_in_month[1] = 29
    std_doy = sum(days_in_month[:month-1]) + day
    if not is_leap and month >= 3:
        return std_doy + 1
    else:
        return std_doy

import pandas as pd

# Compute day of year for each baseline time
base_doy = np.array([doy_from_datetime64(t) for t in base_times])
print("Base DOY values:", base_doy[:10], "...")
print("Unique DOY values:", len(set(base_doy)))
print("DOY range:", min(base_doy), "to", max(base_doy))
