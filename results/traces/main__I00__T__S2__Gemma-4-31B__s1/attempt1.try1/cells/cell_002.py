import xarray as xr
import fsspec
import numpy as np
import pandas as pd
import json

# Check numpy version for 'hazen' method
import numpy as np
print(f"Numpy version: {np.__version__}")

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

# Define region and periods
lat_min, lat_max = 54.13, 55.33
lon_min, lon_max = 14.67, 15.87
baseline_start = '1992-01-01'
baseline_end = '2002-12-31'
target_start = '2004-06-01'
target_end = '2004-08-31'

# Open dataset
with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')

# Slice region
ds_region = ds.sel(
    latitude=slice(lat_min, lat_max),
    longitude=slice(lon_min, lon_max)
)

# Subset time: we need baseline +/- 5 days and target period
# To be safe, we can just take from 1991-12-27 to 2004-08-31
ds_subset = ds_region.sel(time=slice('1991-12-27', '2004-08-31'))

print(ds_subset)
