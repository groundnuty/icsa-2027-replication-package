import fsspec
import xarray as xr
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')
file_path = 'icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
with fs.open(file_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds.latitude.values
    lon = ds.longitude.values

lat_min, lat_max = 58.69, 59.89
lon_min, lon_max = 18.69, 19.89

lat_mask = (lat >= lat_min) & (lat <= lat_max)
lon_mask = (lon >= lon_min) & (lon <= lon_max)

lat_region = lat[lat_mask]
lon_region = lon[lon_mask]

print(f"Latitude range: {lat_region.min()} to {lat_region.max()}, size: {len(lat_region)}")
print(f"Longitude range: {lon_region.min()} to {lon_region.max()}, size: {len(lon_region)}")
