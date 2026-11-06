import xarray as xr
import numpy as np
import pandas as pd
import fsspec
import json
import os

# Constants
REMOTE_PATH = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
LOCAL_PATH = '/work/sst_s2.nc'
LAT_MIN, LAT_MAX = 59.93, 61.13
LON_MIN, LON_MAX = 18.69, 19.89
TARGET_START = '2009-06-01'
TARGET_END = '2009-08-31'
BASELINE_START = '1992-01-01'
BASELINE_END = '2002-12-31'

# Ensure output directory exists
os.makedirs('output', exist_ok=True)

# Download dataset
fs = fsspec.filesystem('onedata')
if not os.path.exists(LOCAL_PATH):
    fs.get(REMOTE_PATH, LOCAL_PATH)

# Open dataset
ds = xr.open_dataset(LOCAL_PATH, engine='h5netcdf')

# Check dimension names
print(f"Dimensions: {ds.dims}")
print(f"Coordinates: {ds.coords}")

# Use the correct names latitude and longitude
# Check if latitude is descending
lat_vals = ds.latitude.values
if lat_vals[0] > lat_vals[-1]:
    lat_slice = slice(LAT_MAX, LAT_MIN)
else:
    lat_slice = slice(LAT_MIN, LAT_MAX)

ds_region = ds.sel(latitude=lat_slice, longitude=slice(LON_MIN, LON_MAX))

print(f"Region lat range: {ds_region.latitude.min().values} to {ds_region.latitude.max().values}")
print(f"Region lon range: {ds_region.longitude.min().values} to {ds_region.longitude.max().values}")
print(f"Time range: {ds_region.time.min().values} to {ds_region.time.max().values}")
