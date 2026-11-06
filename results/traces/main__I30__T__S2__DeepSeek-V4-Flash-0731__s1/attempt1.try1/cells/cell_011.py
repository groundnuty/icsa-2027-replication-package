
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Load data
import fsspec
import xarray as xr

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
    
    base_start = np.datetime64('1991-12-27')
    base_end = np.datetime64('2003-01-05')
    base_mask = (time >= base_start) & (time <= base_end)
    base_idx = np.where(base_mask)[0]
    
    target_sst = ds['analysed_sst'].isel(time=target_idx, latitude=lat_idx, longitude=lon_idx).values
    baseline_sst = ds['analysed_sst'].isel(time=base_idx, latitude=lat_idx, longitude=lon_idx).values
    
    target_time = ds.time.values[target_idx]
    baseline_time = ds.time.values[base_idx]
    region_lat = ds.latitude.values[lat_idx]
    region_lon = ds.longitude.values[lon_idx]

print("Loaded data")
print("baseline_sst shape:", baseline_sst.shape)
print("target_sst shape:", target_sst.shape)
print("baseline_time[0], baseline_time[-1]:", baseline_time[0], baseline_time[-1])
print("target_time[0], target_time[-1]:", target_time[0], target_time[-1])
