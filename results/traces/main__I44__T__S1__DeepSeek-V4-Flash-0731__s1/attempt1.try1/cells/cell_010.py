import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    # Extract region data
    lat_vals = ds['latitude'].values[491:551]  # 60 points
    lon_vals = ds['longitude'].values[616:676]  # 60 points
    
    # Load baseline data (1991-12-27 to 2003-01-05)
    base = ds['analysed_sst'].isel(time=slice(3647, 7675), latitude=slice(491, 551), longitude=slice(616, 676)).load()
    print("Baseline shape:", base.shape)
    print("Baseline dtype:", base.dtype)
    
    # Load target data (2004-06-01 to 2004-08-31)
    target = ds['analysed_sst'].isel(time=slice(8187, 8279), latitude=slice(491, 551), longitude=slice(616, 676)).load()
    print("Target shape:", target.shape)
    print("Target dtype:", target.dtype)
    
    # Save to temp files for later use
    base.to_netcdf('/tmp/base_data.nc')
    target.to_netcdf('/tmp/target_data.nc')
    print("Saved temp files")
    
    # Also save time/lat/lon
    time_vals = ds['time'].values
    np.save('/tmp/time_vals.npy', time_vals)
    np.save('/tmp/lat_vals.npy', lat_vals)
    np.save('/tmp/lon_vals.npy', lon_vals)
    print("Saved time, lat, lon arrays")
