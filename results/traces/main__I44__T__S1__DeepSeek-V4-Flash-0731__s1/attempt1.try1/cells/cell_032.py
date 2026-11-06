import numpy as np
import xarray as xr
import datetime as dt
import pandas as pd

# Verify coordinates match original dataset
import fsspec
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    orig_lat = ds['latitude'].values[491:551]
    orig_lon = ds['longitude'].values[616:676]
    orig_time = ds['time'].values[8187:8279]

# Load our output
out_ds = xr.open_dataset('output/mhw_mask.nc')
out_lat = out_ds['lat'].values
out_lon = out_ds['lon'].values
out_time = out_ds['time'].values

print("Lat match:", np.allclose(orig_lat, out_lat))
print("Lon match:", np.allclose(orig_lon, out_lon))
print("Time match:", np.array_equal(orig_time, out_time))

print("\nOriginal lat:", orig_lat[:5], "...", orig_lat[-5:])
print("Output lat:", out_lat[:5], "...", out_lat[-5:])

print("\nOriginal lon:", orig_lon[:5], "...", orig_lon[-5:])
print("Output lon:", out_lon[:5], "...", out_lon[-5:])

print("\nOriginal time:", orig_time[0], orig_time[-1])
print("Output time:", out_time[0], out_time[-1])
