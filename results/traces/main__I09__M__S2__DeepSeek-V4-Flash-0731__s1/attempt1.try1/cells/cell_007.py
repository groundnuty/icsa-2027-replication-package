
import numpy as np
import pandas as pd

# The time series loaded
# time_sub has 11206 datetime64 values from 1991-12-27 to 2022-08-31
# sst_data shape: (11206, 60, 60)

# Let me rebuild the data loading in a more complete script
import xarray as xr

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

lat_min, lat_max = 54.81, 56.01
lon_min, lon_max = 19.61, 20.81
lat_sel = ds.latitude.values
lon_sel = ds.longitude.values
lat_idx = np.where((lat_sel >= lat_min) & (lat_sel <= lat_max))[0]
lon_idx = np.where((lon_sel >= lon_min) & (lon_sel <= lon_max))[0]

time_vals = ds.time.values
t_start = np.datetime64('1991-12-27')
t_end = np.datetime64('2022-08-31')
t_idx = np.where((time_vals >= t_start) & (time_vals <= t_end))[0]

sst_region = ds['analysed_sst'].isel(
    time=t_idx,
    latitude=slice(lat_idx[0], lat_idx[-1]+1),
    longitude=slice(lon_idx[0], lon_idx[-1]+1)
)
sst_data = sst_region.values.astype(np.float64)
time_sub = time_vals[t_idx]

lat_vals = lat_sel[lat_idx]
lon_vals = lon_sel[lon_idx]

print("sst_data shape:", sst_data.shape)
print("time_sub shape:", time_sub.shape)

# Save to a variable for later use
# Let me save the data so we don't need to reload
np.save('/tmp/sst_data.npy', sst_data)
np.save('/tmp/time_sub.npy', time_sub.astype('datetime64[s]').astype(np.int64))
np.save('/tmp/lat_vals.npy', lat_vals)
np.save('/tmp/lon_vals.npy', lon_vals)

print("Saved to /tmp")
