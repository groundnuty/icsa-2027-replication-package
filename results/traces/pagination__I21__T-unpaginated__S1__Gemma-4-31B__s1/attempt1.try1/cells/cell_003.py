import fsspec
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')
root_dir = 'icsa2027_data_20261101T090944Z/s1z'
sample_file = f'{root_dir}/sst_19820101.nc'

with fs.open(sample_file, "rb") as f:
    ds = xr.open_dataset(f, engine="h5netcdf")
    lat = ds.latitude.values
    lon = ds.longitude.values

lat_min, lat_max = 57.33, 58.53
lon_min, lon_max = 9.03, 10.23

lat_mask = (lat >= lat_min) & (lat <= lat_max)
lon_mask = (lon >= lon_min) & (lon <= lon_max)

print(f"Lat indices: {np.where(lat_mask)[0][0]} to {np.where(lat_mask)[0][-1]}")
print(f"Lon indices: {np.where(lon_mask)[0][0]} to {np.where(lon_mask)[0][-1]}")
print(f"Lat range: {lat[lat_mask].min()} to {lat[lat_mask].max()}")
print(f"Lon range: {lon[lon_mask].min()} to {lon[lon_mask].max()}")
