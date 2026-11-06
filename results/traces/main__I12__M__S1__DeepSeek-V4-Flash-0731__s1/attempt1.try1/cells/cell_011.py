
import xarray as xr
import numpy as np
from datetime import date, timedelta
import os

# Define region
lat_min, lat_max = 56.09, 57.29
lon_min, lon_max = 10.55, 11.75

# Read one file to get grid
ds0 = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20090601.nc', engine='h5netcdf')
lats = ds0.latitude.values
lons = ds0.longitude.values
ds0.close()

lat_mask = (lats >= lat_min) & (lats <= lat_max)
lon_mask = (lons >= lon_min) & (lons <= lon_max)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
lat_start, lat_end = lat_idx[0], lat_idx[-1] + 1
lon_start, lon_end = lon_idx[0], lon_idx[-1] + 1
print(f"Region: lat[{lat_start}:{lat_end}], lon[{lon_start}:{lon_end}]")
print(f"Region lats: {lats[lat_start]} to {lats[lat_end-1]}")
print(f"Region lons: {lons[lon_start]} to {lons[lon_end-1]}")

n_lat = lat_end - lat_start
n_lon = lon_end - lon_start
print(f"Grid: {n_lat}x{n_lon}")

# Get full lat/lon arrays for the region
region_lats = lats[lat_start:lat_end]
region_lons = lons[lon_start:lon_end]
