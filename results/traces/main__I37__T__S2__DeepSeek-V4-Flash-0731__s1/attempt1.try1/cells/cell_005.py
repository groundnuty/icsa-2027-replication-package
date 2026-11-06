
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds.latitude.values
    lon = ds.longitude.values
    
    # Find indices within region bounds
    lat_mask = (lat >= 60.09) & (lat <= 61.29)
    lon_mask = (lon >= 20.01) & (lon <= 21.21)
    lat_idx = np.where(lat_mask)[0]
    lon_idx = np.where(lon_mask)[0]
    print("Lat indices:", lat_idx[0], lat_idx[-1], "count:", len(lat_idx))
    print("Lat values:", lat[lat_idx[0]], lat[lat_idx[-1]])
    print("Lon indices:", lon_idx[0], lon_idx[-1], "count:", len(lon_idx))
    print("Lon values:", lon[lon_idx[0]], lon[lon_idx[-1]])
    
    # Check the grid spacing
    print("Lat spacing:", np.diff(lat)[:5])
    print("Lon spacing:", np.diff(lon)[:5])
