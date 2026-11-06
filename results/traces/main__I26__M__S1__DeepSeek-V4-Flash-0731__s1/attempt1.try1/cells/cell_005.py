
import xarray as xr
import numpy as np
import os

# Load one file to get grid
path = '/data/icsa2027_data_20261101T090944Z/s1z/sst_20070601.nc'
ds = xr.open_dataset(path, engine='h5netcdf')
lat = ds['latitude'].values
lon = ds['longitude'].values
ds.close()

# Find region indices
lat_idx = np.where((lat >= 57.83) & (lat <= 59.03))[0]
lon_idx = np.where((lon >= 17.41) & (lon <= 18.61))[0]
print("lat_idx:", lat_idx[0], "to", lat_idx[-1], "count:", len(lat_idx))
print("lon_idx:", lon_idx[0], "to", lon_idx[-1], "count:", len(lon_idx))
print("lat values:", lat[lat_idx[0]], lat[lat_idx[-1]])
print("lon values:", lon[lon_idx[0]], lon[lon_idx[-1]])

# Check some lat values around boundaries
print("\nLat near 57.83:", lat[lat_idx[0]-1], lat[lat_idx[0]], lat[lat_idx[0]+1])
print("Lat near 59.03:", lat[lat_idx[-1]-1], lat[lat_idx[-1]], lat[lat_idx[-1]+1])
print("Lon near 17.41:", lon[lon_idx[0]-1], lon[lon_idx[0]], lon[lon_idx[0]+1])
print("Lon near 18.61:", lon[lon_idx[-1]-1], lon[lon_idx[-1]], lon[lon_idx[-1]+1])
