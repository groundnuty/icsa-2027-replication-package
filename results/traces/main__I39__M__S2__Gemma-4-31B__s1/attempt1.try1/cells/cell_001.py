import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

# File path
dataset_path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

# Region and time
lat_min, lat_max = 60.49, 61.69
lon_min, lon_max = 17.25, 18.45
target_start = '2010-06-01'
target_end = '2010-08-31'
baseline_start = '1992-01-01'
baseline_end = '2002-12-31'

# Load dataset
ds = xr.open_dataset(dataset_path, engine="h5netcdf")

# Subset the region
ds_region = ds.sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max))

# Print coords to check boundaries
print(f"Lat range: {ds_region.lat.min().values} to {ds_region.lat.max().values}")
print(f"Lon range: {ds_region.lon.min().values} to {ds_region.lon.max().values}")
print(f"Time range: {ds_region.time.min().values} to {ds_region.time.max().values}")
