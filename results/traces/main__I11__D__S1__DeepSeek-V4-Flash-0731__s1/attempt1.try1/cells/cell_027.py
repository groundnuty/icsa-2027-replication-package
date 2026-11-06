
import numpy as np
import xarray as xr
import json
from datetime import date

# Load data
mhw_mask = np.load('/work/mhw_mask.npy')  # (92, 60, 60)
lat_vals = np.load('/work/lat_vals.npy')
lon_vals = np.load('/work/lon_vals.npy')

# Reload target time values
import pandas as pd
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time_vals = ds.time.values
target_idx = np.where((time_vals >= np.datetime64('2021-06-01')) & (time_vals <= np.datetime64('2021-08-31')))[0]
target_time = time_vals[target_idx]
target_dates = [pd.Timestamp(t).date() for t in target_time]

print(f"mhw_mask shape: {mhw_mask.shape}")
print(f"lat_vals shape: {lat_vals.shape}")
print(f"lon_vals shape: {lon_vals.shape}")
print(f"target_time shape: {target_time.shape}")
print(f"target_time range: {target_dates[0]} to {target_dates[-1]}")

# Check mhw_mask dtype and values
print(f"mhw_mask dtype: {mhw_mask.dtype}")
print(f"mhw_mask min: {mhw_mask.min()}, max: {mhw_mask.max()}")

# Create the output netcdf file
import os
os.makedirs('output', exist_ok=True)

# Create xarray dataset
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': target_time,
        'lat': lat_vals,
        'lon': lon_vals,
    }
)

# Set the variable attributes
ds_out['mhw'].attrs['units'] = '1'
ds_out['mhw'].attrs['long_name'] = 'Marine heatwave mask (1 if in per-cell MHW, 0 otherwise)'

# Write to netcdf
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Wrote output/mhw_mask.nc")

# Verify the output
ds_check = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"Verified: shape={ds_check['mhw'].shape}, dtype={ds_check['mhw'].dtype}")
print(f"Verified time: {ds_check.time.values[0]} to {ds_check.time.values[-1]}, n={len(ds_check.time)}")
print(f"Verified lat: {ds_check.lat.values[0]} to {ds_check.lat.values[-1]}, n={len(ds_check.lat)}")
print(f"Verified lon: {ds_check.lon.values[0]} to {ds_check.lon.values[-1]}, n={len(ds_check.lon)}")
print(f"Verified mhw values: min={ds_check['mhw'].min().values}, max={ds_check['mhw'].max().values}")
