
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds.latitude.values
    lon = ds.longitude.values
    
    # Find indices within region
    lat_mask = (lat >= 58.69) & (lat <= 59.89)
    lon_mask = (lon >= 18.69) & (lon <= 19.89)
    
    lat_idx = np.where(lat_mask)[0]
    lon_idx = np.where(lon_mask)[0]
    
    print("Lat indices:", lat_idx[0], "to", lat_idx[-1], "count:", len(lat_idx))
    print("Lon indices:", lon_idx[0], "to", lon_idx[-1], "count:", len(lon_idx))
    print("Lat values:", lat[lat_idx[0]], "to", lat[lat_idx[-1]])
    print("Lon values:", lon[lon_idx[0]], "to", lon[lon_idx[-1]])
