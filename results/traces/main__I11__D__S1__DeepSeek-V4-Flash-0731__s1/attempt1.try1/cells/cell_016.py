
import xarray as xr
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Load the data we need
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Region indices
lat_idx = np.arange(109, 169)
lon_idx = np.arange(373, 433)

# Baseline time indices
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
time_vals = ds.time.values
baseline_mask = (time_vals >= baseline_start) & (time_vals <= baseline_end)
baseline_idx = np.where(baseline_mask)[0]

# Target time indices
target_start = np.datetime64('2021-06-01')
target_end = np.datetime64('2021-08-31')
target_mask = (time_vals >= target_start) & (time_vals <= target_end)
target_idx = np.where(target_mask)[0]

# Load data
print("Loading baseline data...")
baseline_sst = ds['analysed_sst'].isel(time=baseline_idx, latitude=slice(109,169), longitude=slice(373,433)).load().values
baseline_time = time_vals[baseline_idx]
print(f"Baseline SST shape: {baseline_sst.shape}")

print("Loading target data...")
target_sst = ds['analysed_sst'].isel(time=target_idx, latitude=slice(109,169), longitude=slice(373,433)).load().values
target_time = time_vals[target_idx]
print(f"Target SST shape: {target_sst.shape}")

# Convert to float64
baseline_sst = baseline_sst.astype(np.float64)
target_sst = target_sst.astype(np.float64)

# Lat/lon values
lat_vals = ds.latitude.values[lat_idx]
lon_vals = ds.longitude.values[lon_idx]

# Save data for later use
np.save('/work/baseline_sst.npy', baseline_sst)
np.save('/work/target_sst.npy', target_sst)
np.save('/work/baseline_time.npy', baseline_time.astype('datetime64[D]').astype('int64'))
np.save('/work/target_time.npy', target_time.astype('datetime64[D]').astype('int64'))
np.save('/work/lat_vals.npy', lat_vals)
np.save('/work/lon_vals.npy', lon_vals)

print("Data saved.")
print(f"Target time range: {pd.Timestamp(target_time[0])} to {pd.Timestamp(target_time[-1])}")
print(f"Target time count: {len(target_time)}")
