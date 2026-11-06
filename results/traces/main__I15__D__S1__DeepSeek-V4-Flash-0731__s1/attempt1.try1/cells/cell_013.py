
import xarray as xr
import numpy as np
import datetime

# Load data
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values
time_vals = ds.time.values

lat_idx = np.where((lat >= 56.13) & (lat <= 57.33))[0]
lon_idx = np.where((lon >= 17.71) & (lon <= 18.91))[0]

# Target period
target_start = np.datetime64('2019-06-01')
target_end = np.datetime64('2019-08-31')
target_mask = (time_vals >= target_start) & (time_vals <= target_end)
target_time_idx = np.where(target_mask)[0]
target_dates = [pd.Timestamp(t).date() for t in time_vals[target_time_idx]]

import pandas as pd

# Region SST for target
target_sst = ds.analysed_sst[target_time_idx, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].values.astype(np.float64)

# Identify sea cells (finite on every target day)
finite_all = np.all(np.isfinite(target_sst), axis=0)
print("Sea cells:", finite_all.sum(), "out of", finite_all.size)
print("Land cells:", (~finite_all).sum())
