
import xarray as xr
import numpy as np
import pandas as pd
import datetime

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Load data
base_data = ds['analysed_sst'].isel(time=slice(3647, 7675), latitude=slice(260, 320), longitude=slice(485, 545)).load()
target_data = ds['analysed_sst'].isel(time=slice(12935, 13027), latitude=slice(260, 320), longitude=slice(485, 545)).load()

base_times = base_data.time.values
target_times = target_data.time.values

print("Base shape:", base_data.shape)
print("Target shape:", target_data.shape)

# Step 1: Identify sea cells - finite SST on every day of target period
target_values = target_data.values  # (92, 60, 60)
sea_cells = np.all(np.isfinite(target_values), axis=0)  # (60, 60)
print("Sea cells:", sea_cells.sum(), "out of", 60*60)

# Get lat and lon values
lat_vals = ds.latitude.values[260:320]
lon_vals = ds.longitude.values[485:545]
print("Lat range:", lat_vals[0], "to", lat_vals[-1])
print("Lon range:", lon_vals[0], "to", lon_vals[-1])
