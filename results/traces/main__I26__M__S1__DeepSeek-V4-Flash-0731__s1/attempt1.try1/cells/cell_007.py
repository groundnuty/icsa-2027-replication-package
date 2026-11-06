
import xarray as xr
import numpy as np
import os
import datetime

# Define region
lat_min, lat_max = 57.83, 59.03
lon_min, lon_max = 17.41, 18.61

# Load one file to get grid indices
path = '/data/icsa2027_data_20261101T090944Z/s1z/sst_20070601.nc'
ds = xr.open_dataset(path, engine='h5netcdf')
lat = ds['latitude'].values
lon = ds['longitude'].values
lat_idx = np.where((lat >= lat_min) & (lat <= lat_max))[0]
lon_idx = np.where((lon >= lon_min) & (lon <= lon_max))[0]
ds.close()

print(f"Region: {len(lat_idx)} lat × {len(lon_idx)} lon = {len(lat_idx)*len(lon_idx)} cells")

# Helper function: compute doy from date
def date_to_doy(d):
    """Map date to day of year 1-366 using the task's mapping."""
    # Jan=31, Feb=28 (or 29 in leap), etc.
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    year = d.year
    month = d.month
    day = d.day
    
    # Check leap year
    is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    
    doy = day
    for m in range(1, month):
        if m == 2 and is_leap:
            doy += 29
        else:
            doy += days_in_month[m-1]
    
    return doy

# Verify doy mapping
test_dates = [
    datetime.date(2007, 1, 1),
    datetime.date(2007, 2, 28),
    datetime.date(2007, 3, 1),
    datetime.date(2007, 12, 31),
    datetime.date(2008, 2, 29),
    datetime.date(2008, 3, 1),
    datetime.date(2008, 2, 28),
]
for d in test_dates:
    print(f"{d}: doy={date_to_doy(d)}")
