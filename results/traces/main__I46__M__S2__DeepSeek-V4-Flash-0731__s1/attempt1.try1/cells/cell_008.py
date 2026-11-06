
import xarray as xr
import numpy as np
from datetime import datetime, date, timedelta

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

time = ds.time.values
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 64.39) & (lat <= 65.59))[0]
lon_idx = np.where((lon >= 23.41) & (lon <= 24.61))[0]

# Define day-of-year mapping (1-366 by month and day)
# 1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366
# This is a fixed mapping based on month and day (as in a leap year)

def doy_from_month_day(month, day):
    """Return day-of-year from 1-366 based on month and day (leap-year mapping)."""
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# Verify some values
print("Jan 1:", doy_from_month_day(1, 1))  # Should be 1
print("Feb 28:", doy_from_month_day(2, 28))  # Should be 59
print("Feb 29:", doy_from_month_day(2, 29))  # Should be 60
print("Mar 1:", doy_from_month_day(3, 1))  # Should be 61
print("Dec 31:", doy_from_month_day(12, 31))  # Should be 366
