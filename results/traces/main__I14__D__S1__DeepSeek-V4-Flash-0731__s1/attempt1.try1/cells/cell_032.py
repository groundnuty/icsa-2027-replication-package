
import numpy as np
import xarray as xr
import pandas as pd
import json
import os

# Load all needed data
target_sst = np.load('/work/target_sst.npy')
target_times = np.load('/work/target_times.npy')
target_pd = pd.to_datetime(target_times)
per_cell_mhw = np.load('/work/per_cell_mhw.npy')
lat_indices = np.load('/work/lat_indices.npy')
lon_indices = np.load('/work/lon_indices.npy')

# Load the original dataset to get coordinate values
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
lat_vals = ds.latitude.values[lat_indices]
lon_vals = ds.longitude.values[lon_indices]
time_vals = ds.time.values

# Get the target time values
target_time_vals = time_vals[np.where((time_vals >= np.datetime64('2015-06-01')) & (time_vals <= np.datetime64('2015-08-31')))[0]]
print(f"Target time values: {target_time_vals[0]} to {target_time_vals[-1]}, count={len(target_time_vals)}")
print(f"Target pd: {target_pd[0]} to {target_pd[-1]}, count={len(target_pd)}")
print(f"Lat values: {lat_vals[0]} to {lat_vals[-1]}, count={len(lat_vals)}")
print(f"Lon values: {lon_vals[0]} to {lon_vals[-1]}, count={len(lon_vals)}")

# Construct mhw_mask
# per_cell_mhw shape: (92, 60, 60) - already in the correct format
# We need to use uint8
mhw_mask = per_cell_mhw.astype(np.uint8)

# Create xarray dataset
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': target_time_vals,
        'lat': lat_vals,
        'lon': lon_vals
    }
)

# Ensure output directory exists
os.makedirs('/work/output', exist_ok=True)

# Write to netcdf
ds_out.to_netcdf('/work/output/mhw_mask.nc', engine='h5netcdf')
print("Written mhw_mask.nc")

# Check the file
ds_check = xr.open_dataset('/work/output/mhw_mask.nc', engine='h5netcdf')
print(ds_check)
print(f"\nmhw dtype: {ds_check['mhw'].dtype}")
print(f"mhw shape: {ds_check['mhw'].shape}")
print(f"mhw min: {ds_check['mhw'].min().values}, max: {ds_check['mhw'].max().values}")
