
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Reconstruct dates
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
import xarray as xr
ds = xr.open_dataset(path, engine="h5netcdf")
time = ds['time'].values
time_dates = pd.to_datetime(time).date

pool_start = date(1991, 12, 27)
pool_end = date(2003, 1, 5)
target_start = date(2005, 6, 1)
target_end = date(2005, 8, 31)

pool_mask = (time_dates >= pool_start) & (time_dates <= pool_end)
target_mask = (time_dates >= target_start) & (time_dates <= target_end)
time_idx = np.where(pool_mask | target_mask)[0]

load_dates = [time_dates[i] for i in time_idx]
print("First few load dates:", load_dates[:5])
print("Last few load dates:", load_dates[-5:])

# Split into pool and target indices within the loaded array
pool_local = np.where(pool_mask[time_idx])[0]
target_local = np.where(target_mask[time_idx])[0]
print("pool local range:", pool_local[0], pool_local[-1], "count:", len(pool_local))
print("target local range:", target_local[0], target_local[-1], "count:", len(target_local))
print("pool dates:", load_dates[pool_local[0]], "to", load_dates[pool_local[-1]])
print("target dates:", load_dates[target_local[0]], "to", load_dates[target_local[-1]])
