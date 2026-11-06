import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
import os
from datetime import datetime, timedelta

# Setup filesystem
fs = fsspec.filesystem('onedata')
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'
if not os.path.exists(local_path):
    fs.get(remote_path, local_path)

ds = xr.open_dataset(local_path, engine="h5netcdf")

# Region
lat_min, lat_max = 57.57, 58.77
lon_min, lon_max = 10.25, 11.45

# Target period
target_start = '2004-06-01'
target_end = '2004-08-31'

# Baseline window for pooling
# Baseline dates: 1992-01-01 to 2002-12-31
# Windows are +/- 5 days
baseline_start_win = '1991-12-27'
baseline_end_win = '2003-01-05'

# Slice region
ds_reg = ds.sel(latitude=slice(lat_min, lat_max), longitude=slice(lon_min, lon_max))

# Slice time
# We need baseline window and target period.
# Since they are separated, we can either load them separately or load the range.
# 1991-12-27 to 2004-08-31 is a long range.
# Let's load baseline and target separately to save memory.

def get_doy(dt):
    # Manual doy mapping as requested
    month = dt.month
    day = dt.day
    # Days in months for leap year
    days_in_month = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    # For non-leap year, we still use the 366-day map.
    # If it's Feb 29 in a non-leap year, it doesn't exist.
    # The request says "Map every date to a day of year from 1 to 366 by month and day"
    # This means for any date, its doy is sum of days in prev months + day.
    # But for non-leap years, the 29th of Feb is missing.
    # Let's check: "1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61"
    # This confirms that for a non-leap year, we go from 59 to 61.
    
    # To implement this correctly:
    # If month > 2, we need to know if we are in a leap year to decide if Feb had 29 days?
    # No, the mapping is "by month and day", not by absolute day of year in that specific year.
    # "1 March = 61" always.
    # So, doy = sum([31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][:month-1]) + day
    # Wait, if I use 29 for February, then March 1 is 31+29+1 = 61. Correct.
    # February 28 is 31+28 = 59. Correct.
    # February 29 is 31+29 = 60. Correct.
    
    month_offsets = [0, 0, 31, 60, 91, 121, 151, 181, 212, 243, 273, 304, 334]
    return month_offsets[month] + day

# Let's verify the mapping with a few dates
print(f"2004-02-28 doy: {get_doy(datetime(2004, 2, 28))}")
print(f"2004-02-29 doy: {get_doy(datetime(2004, 2, 29))}")
print(f"2004-03-01 doy: {get_doy(datetime(2004, 3, 1))}")
print(f"2003-02-28 doy: {get_doy(datetime(2003, 2, 28))}")
print(f"2003-03-01 doy: {get_doy(datetime(2003, 3, 1))}")
