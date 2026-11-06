
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

# Region indices
lat_idx = slice(217, 277)  # 60 cells, lat 57.84 to 59.02
lon_idx = slice(421, 481)  # 60 cells, lon 17.42 to 18.60

# Baseline window
base_start_idx = 3647  # 1991-12-27
base_end_idx = 7674    # 2003-01-05
tgt_start_idx = 9282   # 2007-06-01
tgt_end_idx = 9373     # 2007-08-31

# Load baseline and target data
print("Loading data...")
base_sub = ds.analysed_sst.isel(time=slice(base_start_idx, base_end_idx+1),
                                 latitude=lat_idx, longitude=lon_idx)
base_data = base_sub.values  # (4028, 60, 60)
print(f"Baseline shape: {base_data.shape}")

tgt_sub = ds.analysed_sst.isel(time=slice(tgt_start_idx, tgt_end_idx+1),
                                latitude=lat_idx, longitude=lon_idx)
tgt_data = tgt_sub.values  # (92, 60, 60)
print(f"Target shape: {tgt_data.shape}")

# Get time arrays
time_all = ds.time.values
base_time = time_all[base_start_idx:base_end_idx+1]
tgt_time = time_all[tgt_start_idx:tgt_end_idx+1]

# Get lat/lon coordinates
lat_vals = ds.latitude.values[217:277]
lon_vals = ds.longitude.values[421:481]

print(f"Base time: {base_time[0]} to {base_time[-1]}")
print(f"Tgt time: {tgt_time[0]} to {tgt_time[-1]}")
print(f"Lat range: {lat_vals[0]} to {lat_vals[-1]}")
print(f"Lon range: {lon_vals[0]} to {lon_vals[-1]}")
