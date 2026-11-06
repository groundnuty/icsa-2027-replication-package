
import numpy as np
import xarray as xr
import pandas as pd
import json
import os

# Load data
mhw_mask = np.load('/work/mhw_mask.npy')
lat = np.load('/work/lat.npy')
lon = np.load('/work/lon.npy')
target_time = np.load('/work/target_time.npy').astype('datetime64[D]')

# Load the dataset to get original coordinate values
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
sst_region = ds.analysed_sst.sel(latitude=slice(57.83, 59.03), longitude=slice(17.41, 18.61))
target = sst_region.sel(time=slice('2008-06-01', '2008-08-31'))

# mhw_mask has shape (92, 60, 60)
print("mhw_mask shape:", mhw_mask.shape)
print("mhw dtype:", mhw_mask.dtype)

# Create output directory
os.makedirs('output', exist_ok=True)

# Create xarray dataset
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': target.time.values,
        'lat': target.latitude.values,
        'lon': target.longitude.values
    }
)
ds_out['mhw'].attrs['long_name'] = 'marine heatwave indicator'
ds_out['mhw'].attrs['units'] = '1=inside per-cell MHW, 0=not'

# Write NetCDF
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Written mhw_mask.nc")

# Verify
ds_check = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(ds_check)
print("mhw shape:", ds_check.mhw.shape)
print("mhw dtype:", ds_check.mhw.dtype)
print("mhw values unique:", np.unique(ds_check.mhw.values))
