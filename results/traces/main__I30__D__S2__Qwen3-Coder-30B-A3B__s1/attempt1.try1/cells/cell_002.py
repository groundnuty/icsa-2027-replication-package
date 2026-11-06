import fsspec
import xarray as xr
import numpy as np
import os

# Create filesystem
fs = fsspec.filesystem('onedata')

# Download the file
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'

print("Downloading file...")
fs.get(remote_path, local_path)
print("Download complete")

# Open with xarray
print("Opening dataset...")
ds = xr.open_dataset(local_path, engine='h5netcdf')
print("Dataset opened successfully")

# Print basic information
print("\nDataset dims:", ds.dims)
print("Dataset coords:", list(ds.coords.keys()))
print("Dataset vars:", list(ds.data_vars.keys()))

# Examine coordinates
print("\nTime dim:", ds.dims.get('time', 'Not found'))
print("Latitude dim:", ds.dims.get('lat', 'Not found'))  
print("Longitude dim:", ds.dims.get('lon', 'Not found'))

if 'time' in ds.coords:
    print("Time range:", ds.time.min().values, "to", ds.time.max().values)
if 'lat' in ds.coords:
    print("Latitude range:", ds.lat.min().values, "to", ds.lat.max().values)
if 'lon' in ds.coords:
    print("Longitude range:", ds.lon.min().values, "to", ds.lon.max().values)

# Look at the SST variable
if 'sst' in ds.data_vars:
    print("\nSST variable shape:", ds.sst.shape)
    print("SST variable dims:", ds.sst.dims)
    print("Sample SST values (first few time steps):")
    print(ds.sst.isel(time=slice(0, 5)).values)