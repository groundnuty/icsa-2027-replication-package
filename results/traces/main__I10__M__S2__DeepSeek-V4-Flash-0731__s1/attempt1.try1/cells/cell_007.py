
import numpy as np
from datetime import date, timedelta
import xarray as xr
import pandas as pd

# Reload data
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
lat = ds['latitude'].values
lon = ds['longitude'].values
time = ds['time'].values
time_dates = pd.to_datetime(time).date

lat_mask = (lat >= 55.67) & (lat <= 56.87)
lon_mask = (lon >= 16.45) & (lon <= 17.65)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]

pool_start = date(1991, 12, 27)
pool_end = date(2003, 1, 5)
target_start = date(2005, 6, 1)
target_end = date(2005, 8, 31)

pool_mask = (time_dates >= pool_start) & (time_dates <= pool_end)
target_mask = (time_dates >= target_start) & (time_dates <= target_end)
time_idx = np.where(pool_mask | target_mask)[0]

# Load SST data (keeping in memory)
sst = ds['analysed_sst'].isel(time=time_idx, latitude=lat_idx, longitude=lon_idx).values
print("Loaded sst:", sst.shape)

# Determine pool local indices
pool_local = np.where(pool_mask[time_idx])[0]
target_local = np.where(target_mask[time_idx])[0]
print("pool_local:", pool_local[0], pool_local[-1], "count:", len(pool_local))
print("target_local:", target_local[0], target_local[-1], "count:", len(target_local))

# Load dates for pool period
pool_dates = [time_dates[i] for i in time_idx[pool_local]]
target_dates = [time_dates[i] for i in time_idx[target_local]]
print("pool dates:", pool_dates[0], "to", pool_dates[-1])
print("target dates:", target_dates[0], "to", target_dates[-1])

# Verify target dates
print("First 5 target:", target_dates[:5])
print("Last 5 target:", target_dates[-5:])
