import fsspec
import xarray as xr
import numpy as np
from datetime import date, timedelta

fs = fsspec.filesystem('onedata')

# Region bounds
lat_min, lat_max = 63.31, 64.51
lon_min, lon_max = 21.31, 22.51

# Get grid indices from a sample file
path = 'icsa2027_data_20261101T090944Z/s1z/sst_20040601.nc'
with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds['latitude'].values
    lon = ds['longitude'].values
    
    lat_idx = np.where((lat >= lat_min) & (lat <= lat_max))[0]
    lon_idx = np.where((lon >= lon_min) & (lon <= lon_max))[0]
    lat_start, lat_end = lat_idx[0], lat_idx[-1] + 1
    lon_start, lon_end = lon_idx[0], lon_idx[-1] + 1
    
    region_lat = lat[lat_start:lat_end]
    region_lon = lon[lon_start:lon_end]
    print(f"Region lat: {region_lat.shape}, {region_lat[0]} to {region_lat[-1]}")
    print(f"Region lon: {region_lon.shape}, {region_lon[0]} to {region_lon[-1]}")
    print(f"lat_idx: {lat_start} to {lat_end-1}")
    print(f"lon_idx: {lon_start} to {lon_end-1}")
