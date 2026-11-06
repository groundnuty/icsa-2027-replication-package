import xarray as xr
import fsspec
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'

# Read one file to get coordinates
with fs.open(f'{path}/sst_19820101.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds.latitude.values
    lon = ds.longitude.values

lat_min, lat_max = 55.67, 56.87
lon_min, lon_max = 16.45, 17.65

lat_mask = (lat >= lat_min) & (lat <= lat_max)
lon_mask = (lon >= lon_min) & (lon <= lon_max)

lat_indices = np.where(lat_mask)[0]
lon_indices = np.where(lon_mask)[0]

print(f"Lat indices: {lat_indices}")
print(f"Lon indices: {lon_indices}")
print(f"Region size: {len(lat_indices)} x {len(lon_indices)}")
