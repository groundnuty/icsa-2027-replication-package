
import numpy as np
import datetime as dt
import xarray as xr
import json
import os
import gc

# ============================================================
# Load data
# ============================================================
print("Loading data...")
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat_min_idx, lat_max_idx = 34, 93
lon_min_idx, lon_max_idx = 213, 272

times = ds.time.values
lats = ds.latitude.values[lat_min_idx:lat_max_idx+1]
lons = ds.longitude.values[lon_min_idx:lon_max_idx+1]

baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
target_start = np.datetime64('2014-06-01')
target_end = np.datetime64('2014-08-31')

baseline_mask = (times >= baseline_start) & (times <= baseline_end)
target_mask = (times >= target_start) & (times <= target_end)

baseline_idx = np.where(baseline_mask)[0]
target_idx = np.where(target_mask)[0]

# Load baseline and target SST for the region
baseline_sst = ds['analysed_sst'].isel(time=baseline_idx, latitude=slice(lat_min_idx, lat_max_idx+1), longitude=slice(lon_min_idx, lon_max_idx+1)).values.astype(np.float64)
target_sst = ds['analysed_sst'].isel(time=target_idx, latitude=slice(lat_min_idx, lat_max_idx+1), longitude=slice(lon_min_idx, lon_max_idx+1)).values.astype(np.float64)

baseline_dates = [dt.datetime.utcfromtimestamp(t.astype('datetime64[us]').astype(np.int64) / 1e6) for t in times[baseline_idx]]
target_dates = [dt.datetime.utcfromtimestamp(t.astype('datetime64[us]').astype(np.int64) / 1e6) for t in times[target_idx]]

print(f"Baseline shape: {baseline_sst.shape}")
print(f"Target shape: {target_sst.shape}")
print(f"Baseline dates: {baseline_dates[0]} to {baseline_dates[-1]}")
print(f"Target dates: {target_dates[0]} to {target_dates[-1]}")

# Free memory from ds
del ds
gc.collect()
