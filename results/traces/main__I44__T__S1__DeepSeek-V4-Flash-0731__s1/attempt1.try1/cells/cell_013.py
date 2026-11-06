import numpy as np
import xarray as xr
import datetime as dt

# Load saved data
base_ds = xr.open_dataset('/tmp/base_data.nc')
target_ds = xr.open_dataset('/tmp/target_data.nc')

base_sst = base_ds['analysed_sst'].values.astype(np.float64)  # (4028, 60, 60)
target_sst = target_ds['analysed_sst'].values.astype(np.float64)  # (92, 60, 60)
base_time = base_ds['time'].values
target_time = target_ds['time'].values

# Convert to datetime.date objects
import pandas as pd
base_dates = [pd.Timestamp(t).to_pydatetime().date() for t in base_time]
target_dates = [pd.Timestamp(t).to_pydatetime().date() for t in target_time]

print("Base dates:", base_dates[0], base_dates[-1], len(base_dates))
print("Target dates:", target_dates[0], target_dates[-1], len(target_dates))

# Check what the baseline year range looks like
# The baseline is 1992-2002, plus windows to 1991-12-27 and 2003-01-05
# The extended baseline data we loaded goes from 1991-12-27 to 2003-01-05

# Function to compute day of year (1-366)
def day_of_year(date):
    """Map date to day of year 1-366.
    1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366
    """
    y = date.year
    # Check if leap year
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    
    # Days in each month
    month_days = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    doy = sum(month_days[:date.month-1]) + date.day
    return doy

# Test
print(day_of_year(dt.date(1992, 1, 1)))  # should be 1
print(day_of_year(dt.date(1992, 2, 28)))  # should be 59
print(day_of_year(dt.date(1992, 2, 29)))  # should be 60
print(day_of_year(dt.date(1992, 3, 1)))   # should be 61
print(day_of_year(dt.date(1992, 12, 31))) # should be 366
print(day_of_year(dt.date(1993, 2, 28)))  # should be 59
print(day_of_year(dt.date(1993, 3, 1)))   # should be 61
print(day_of_year(dt.date(1993, 12, 31))) # should be 366
