
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Region bounds
lat_min, lat_max = 61.57, 62.77
lon_min, lon_max = 20.17, 21.37

# Get lat/lon indices for region
lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
lat_mask = (lat_vals >= lat_min) & (lat_vals <= lat_max)
lon_mask = (lon_vals >= lon_min) & (lon_vals <= lon_max)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]
print(f"Lat indices: {len(lat_idx)} ({lat_idx[0]}-{lat_idx[-1]})")
print(f"Lon indices: {len(lon_idx)} ({lon_idx[0]}-{lon_idx[-1]})")

# Extract baseline data (1991-12-27 to 2003-01-05) for region
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')

# Get time indices
times = ds.time.values
base_mask = (times >= baseline_start) & (times <= baseline_end)
base_times = times[base_mask]
print(f"Baseline times: {len(base_times)}")

# Extract the region data for baseline
baseline_sst = ds.analysed_sst.isel(time=base_mask, latitude=lat_idx, longitude=lon_idx)
print(f"Baseline data shape: {baseline_sst.shape}")
print(f"Baseline data size (MB): {baseline_sst.nbytes / 1e6:.1f}")
print(f"Baseline data memory: {baseline_sst.nbytes / 1e9:.2f} GB")
