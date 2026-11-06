
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
    lat = ds.latitude.values
    lon = ds.longitude.values
    time = ds.time.values
    
    lat_idx = np.where((lat >= 58.69) & (lat <= 59.89))[0]
    lon_idx = np.where((lon >= 18.69) & (lon <= 19.89))[0]
    
    target_start = np.datetime64('2010-06-01')
    target_end = np.datetime64('2010-08-31')
    target_mask = (time >= target_start) & (time <= target_end)
    target_idx = np.where(target_mask)[0]
    
    # Load target data
    target_sst = ds['analysed_sst'].isel(time=target_idx, latitude=lat_idx, longitude=lon_idx).values
    target_time = ds.time.values[target_idx]
    target_lat = ds.latitude.values[lat_idx]
    target_lon = ds.longitude.values[lon_idx]
    
    print("Target shape:", target_sst.shape)
    print("Target dtype:", target_sst.dtype)
    print("Target min/max:", np.nanmin(target_sst), np.nanmax(target_sst))
    print("NaN count:", np.isnan(target_sst).sum())
    print("Target time:", target_time[0], "to", target_time[-1])
