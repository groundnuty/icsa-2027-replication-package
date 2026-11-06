
import xarray as xr
import fsspec
import numpy as np
import pandas as pd

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Region bounds
lat_min, lat_max = 58.69, 59.89
lon_min, lon_max = 18.69, 19.89

lat = ds.latitude.values
lon = ds.longitude.values
time = pd.to_datetime(ds.time.values)

# Find indices in region
lat_idx = np.where((lat >= lat_min) & (lat <= lat_max))[0]
lon_idx = np.where((lon >= lon_min) & (lon <= lon_max))[0]
print("lat_idx:", lat_idx[0], lat_idx[-1], "count:", len(lat_idx))
print("lon_idx:", lon_idx[0], lon_idx[-1], "count:", len(lon_idx))
print("lat values:", lat[lat_idx[0]], lat[lat_idx[-1]])
print("lon values:", lon[lon_idx[0]], lon[lon_idx[-1]])

# Target period
t_start = pd.Timestamp('2010-06-01')
t_end = pd.Timestamp('2010-08-31')
t_mask = (time >= t_start) & (time <= t_end)
t_idx = np.where(t_mask)[0]
print("target time indices:", t_idx[0], t_idx[-1], "count:", len(t_idx))

# Baseline period 1992-01-01 to 2002-12-31, plus the ±5 day window extension
b_start = pd.Timestamp('1991-12-27')
b_end = pd.Timestamp('2003-01-05')
b_mask = (time >= b_start) & (time <= b_end)
b_idx = np.where(b_mask)[0]
print("baseline time indices:", b_idx[0], b_idx[-1], "count:", len(b_idx))
