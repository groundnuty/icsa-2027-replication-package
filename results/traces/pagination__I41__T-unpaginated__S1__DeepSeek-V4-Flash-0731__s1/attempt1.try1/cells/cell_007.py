
import fsspec
import xarray as xr
import numpy as np
import datetime
import os

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# First, get the region indices from a sample file
f = fs.open(f'{base}/sst_20210601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 61.57) & (lat <= 62.77))[0]
lon_idx = np.where((lon >= 20.17) & (lon <= 21.37))[0]
lat_min_i, lat_max_i = lat_idx.min(), lat_idx.max()
lon_min_i, lon_max_i = lon_idx.min(), lon_idx.max()
print(f"Region indices: lat [{lat_min_i}, {lat_max_i}], lon [{lon_min_i}, {lon_max_i}]")
print(f"Region lat values: {lat[lat_min_i]} to {lat[lat_max_i]}")
print(f"Region lon values: {lon[lon_min_i]} to {lon[lon_max_i]}")
ds.close()

# Define date ranges
baseline_start = datetime.date(1991, 12, 27)
baseline_end = datetime.date(2003, 1, 5)
target_start = datetime.date(2021, 6, 1)
target_end = datetime.date(2021, 8, 31)

# Function to compute day of year (1-366, with Feb 29 = 60)
def day_of_year(d):
    """Compute day of year 1-366. Jan 1=1, Feb 28=59, Feb 29=60, Mar 1=61, etc."""
    year_start = datetime.date(d.year, 1, 1)
    return (d - year_start).days + 1

# Test
print("Jan 1:", day_of_year(datetime.date(2021, 1, 1)))
print("Feb 28:", day_of_year(datetime.date(2021, 2, 28)))
print("Mar 1:", day_of_year(datetime.date(2021, 3, 1)))
print("Dec 31:", day_of_year(datetime.date(2021, 12, 31)))
print("Feb 29:", day_of_year(datetime.date(2020, 2, 29)))
print("Mar 1 (leap):", day_of_year(datetime.date(2020, 3, 1)))
