import xarray as xr
import numpy as np
import pandas as pd
import datetime
import json
import os

# Define constants
REGION = {"lat_min": 62.25, "lat_max": 63.45, "lon_min": 18.73, "lon_max": 19.93}
TARGET_START = "2017-06-01"
TARGET_END = "2017-08-31"
BASELINE_START = "1992-01-01"
BASELINE_END = "2002-12-31"
REMOTE_PATH = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
LOCAL_PATH = "/work/sst_s2.nc"

def get_doy(dt):
    """Map date to DOY 1-366 based on month and day."""
    # Month offsets for non-leap year
    month_offsets = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    doy = month_offsets[dt.month - 1] + dt.day
    if dt.month > 2:
        # We want 1 Mar = 61, but month_offsets[2] = 59.
        # In our logic, Feb 29 is 60.
        # Let's adjust:
        # Jan: 1-31
        # Feb: 32-59
        # Feb 29: 60
        # Mar: 61-91 ...
        # This means if month > 2, we add 1 for Feb 29.
        # But wait, the offsets are for non-leap.
        # Jan 31: offset[0]+31 = 31.
        # Feb 28: offset[1]+28 = 31+28 = 59.
        # Mar 1: offset[2]+1 = 59+1 = 60. -> Should be 61.
        # So if month > 2, add 1.
        return doy + 1
    return doy

# Correct get_doy mapping
def get_doy_fixed(dt):
    # Fixed mapping based on month and day
    # Jan: 1-31
    # Feb: 32-59 (up to 28th)
    # Feb 29: 60
    # Mar: 61-91
    # ...
    # Dec 31: 366
    # This means if it's Feb 29, return 60.
    # If it's Mar or later, we treat it as if Feb had 29 days.
    # Standard yday for leap year: Jan 1 (1), Feb 28 (59), Feb 29 (60), Mar 1 (61)
    # Standard yday for non-leap: Jan 1 (1), Feb 28 (59), Mar 1 (60)
    # So for non-leap, if yday > 59, add 1.
    yday = (dt - datetime.date(dt.year, 1, 1)).days + 1
    is_leap = (dt.year % 4 == 0 and (dt.year % 100 != 0 or dt.year % 400 == 0))
    if not is_leap and yday > 59:
        return yday + 1
    return yday

# Download and load
import fsspec
fs = fsspec.filesystem('onedata')
fs.get(REMOTE_PATH, LOCAL_PATH)

ds = xr.open_dataset(LOCAL_PATH, engine="h5netcdf")
sst_var = 'thetao' # Need to check the variable name

# Let's inspect the dataset first
print(ds)
