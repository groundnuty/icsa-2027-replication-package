import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds['latitude'].values
    lon = ds['longitude'].values
    time = ds['time'].values
    
    # Find indices for region
    lat_mask = (lat >= 63.31) & (lat <= 64.51)
    lon_mask = (lon >= 21.31) & (lon <= 22.51)
    
    lat_idx = np.where(lat_mask)[0]
    lon_idx = np.where(lon_mask)[0]
    
    print("Lat indices:", lat_idx[0], lat_idx[-1], "count:", len(lat_idx))
    print("Lon indices:", lon_idx[0], lon_idx[-1], "count:", len(lon_idx))
    print("Lat values:", lat[lat_idx[0]], lat[lat_idx[-1]])
    print("Lon values:", lon[lon_idx[0]], lon[lon_idx[-1]])
    print()
    
    # Find target period indices
    target_start = np.datetime64('2004-06-01')
    target_end = np.datetime64('2004-08-31')
    target_mask = (time >= target_start) & (time <= target_end)
    target_idx = np.where(target_mask)[0]
    print("Target time indices:", target_idx[0], target_idx[-1], "count:", len(target_idx))
    print("Target dates:", time[target_idx[0]], time[target_idx[-1]])
    
    # Find baseline period indices (including windows)
    base_start = np.datetime64('1991-12-27')
    base_end = np.datetime64('2003-01-05')
    base_mask = (time >= base_start) & (time <= base_end)
    base_idx = np.where(base_mask)[0]
    print("Baseline time indices:", base_idx[0], base_idx[-1], "count:", len(base_idx))
    print("Baseline dates:", time[base_idx[0]], time[base_idx[-1]])
