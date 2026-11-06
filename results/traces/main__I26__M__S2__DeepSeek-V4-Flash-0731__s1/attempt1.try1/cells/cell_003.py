
import xarray as xr
import numpy as np

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

# Use dask/lazy operations
# Find indices for our region
lat = ds.latitude.values
lon = ds.longitude.values

lat_idx = np.where((lat >= 57.83) & (lat <= 59.03))[0]
lon_idx = np.where((lon >= 17.41) & (lon <= 18.61))[0]

print(f"lat_idx: {lat_idx[0]} to {lat_idx[-1]}, count={len(lat_idx)}")
print(f"lon_idx: {lon_idx[0]} to {lon_idx[-1]}, count={len(lon_idx)}")
print(f"Lat values: {lat[lat_idx[0]]} to {lat[lat_idx[-1]]}")
print(f"Lon values: {lon[lon_idx[0]]} to {lon[lon_idx[-1]]}")

# Check time indices for baseline (1992-2002) and target (2007)
time = ds.time.values
# Baseline: 1992-01-01 to 2002-12-31, plus window 1991-12-27 to 2003-01-05
# Target: 2007-06-01 to 2007-08-31

import pandas as pd
base_start = pd.Timestamp('1991-12-27')
base_end = pd.Timestamp('2003-01-05')
tgt_start = pd.Timestamp('2007-06-01')
tgt_end = pd.Timestamp('2007-08-31')

print(f"\nTime range: {time[0]} to {time[-1]}")
print(f"Time step check (first 5): {time[:5]}")
