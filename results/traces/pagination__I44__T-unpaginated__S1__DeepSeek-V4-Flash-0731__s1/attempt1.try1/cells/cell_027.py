import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')

# Load a sample file to get coordinate values
path = 'icsa2027_data_20261101T090944Z/s1z/sst_20040601.nc'
with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    lat = ds['latitude'].values
    lon = ds['longitude'].values
    
    # Check the time dimension
    time_vals = ds['time'].values
    print(f"Time: {time_vals}")
    
    # Check if all files have the same lat/lon
    print(f"Lat shape: {lat.shape}")
    print(f"Lon shape: {lon.shape}")
    
    # Also check attributes
    print(f"Lat attrs: {ds['latitude'].attrs}")
    print(f"Lon attrs: {ds['longitude'].attrs}")
    print(f"Time attrs: {ds['time'].attrs}")

# Check another file to see if coordinates are the same
path2 = 'icsa2027_data_20261101T090944Z/s1z/sst_20040831.nc'
with fs.open(path2, 'rb') as f:
    ds2 = xr.open_dataset(f, engine='h5netcdf')
    lat2 = ds2['latitude'].values
    lon2 = ds2['longitude'].values
    time2 = ds2['time'].values
    print(f"\nTime2: {time2}")
    print(f"Lat same: {np.allclose(lat, lat2)}")
    print(f"Lon same: {np.allclose(lon, lon2)}")
