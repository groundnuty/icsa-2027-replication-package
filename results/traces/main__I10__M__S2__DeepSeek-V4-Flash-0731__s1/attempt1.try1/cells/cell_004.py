
import xarray as xr
import numpy as np
from datetime import date, timedelta

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

lat = ds['latitude'].values
lon = ds['longitude'].values
time = ds['time'].values

lat_mask = (lat >= 55.67) & (lat <= 56.87)
lon_mask = (lon >= 16.45) & (lon <= 17.65)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print("lat_idx", lat_idx.min(), lat_idx.max(), "count", len(lat_idx))
print("lon_idx", lon_idx.min(), lon_idx.max(), "count", len(lon_idx))

# Determine time indices
pool_start = date(1991, 12, 27)
pool_end = date(2003, 1, 5)
target_start = date(2005, 6, 1)
target_end = date(2005, 8, 31)

# Convert numpy datetime64 to python dates
import pandas as pd
time_dates = pd.to_datetime(time).date

# Find time indices
pool_mask = (time_dates >= pool_start) & (time_dates <= pool_end)
target_mask = (time_dates >= target_start) & (time_dates <= target_end)
time_idx = np.where(pool_mask | target_mask)[0]
print("pool time idx:", np.where(pool_mask)[0][0], np.where(pool_mask)[0][-1])
print("target time idx:", np.where(target_mask)[0][0], np.where(target_mask)[0][-1])
print("total time points to load:", len(time_idx))

# Load subset
sst = ds['analysed_sst'].isel(time=time_idx, latitude=lat_idx, longitude=lon_idx).values
print("sst shape:", sst.shape, sst.dtype)
print("sst finite:", np.isfinite(sst).sum(), "of", sst.size)
print("sst range:", np.nanmin(sst), np.nanmax(sst))
