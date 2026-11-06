
import os
import re
import numpy as np
import xarray as xr
from datetime import date, timedelta

base_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# Region indices
lat_min_val, lat_max_val = 60.09, 61.29
lon_min_val, lon_max_val = 20.01, 21.21

# Open a sample to get coordinates
sample = xr.open_dataset(os.path.join(base_dir, 'sst_20030601.nc'), engine='h5netcdf')
lat = sample.latitude.values
lon = sample.longitude.values
lat_idx = np.where((lat >= lat_min_val) & (lat <= lat_max_val))[0]
lon_idx = np.where((lon >= lon_min_val) & (lon <= lon_max_val))[0]
lat_region = lat[lat_idx]
lon_region = lon[lon_idx]
sample.close()

print(f"Region: {len(lat_region)} x {len(lon_region)} = {len(lat_region)*len(lon_region)} cells")

# Function to map date to day of year (1-366)
def day_of_year(d):
    """Map date to day of year: 1 Jan=1, 28 Feb=59, 29 Feb=60, 1 Mar=61, ..., 31 Dec=366"""
    start = date(d.year, 1, 1)
    return (d - start).days + 1

# Test
print(f"2003-01-01 -> {day_of_year(date(2003,1,1))}")
print(f"2003-02-28 -> {day_of_year(date(2003,2,28))}")
print(f"2004-02-29 -> {day_of_year(date(2004,2,29))}")
print(f"2003-03-01 -> {day_of_year(date(2003,3,1))}")
print(f"2003-12-31 -> {day_of_year(date(2003,12,31))}")
print(f"2003-06-01 -> {day_of_year(date(2003,6,1))}")
print(f"2003-08-31 -> {day_of_year(date(2003,8,31))}")
