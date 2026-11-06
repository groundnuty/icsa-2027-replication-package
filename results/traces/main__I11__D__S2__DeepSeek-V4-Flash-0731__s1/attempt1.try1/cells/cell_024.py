
import numpy as np
import pandas as pd
import xarray as xr
import json
import os

# Reload everything
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))
target = region.sel(time=slice('2021-06-01', '2021-08-31'))

mhw_mask = np.load('/work/mhw_mask.npy')  # (60, 60, n_time)

# Create output directory
os.makedirs('output', exist_ok=True)

# Write mhw_mask.nc
# mhw_mask has shape (60, 60, n_time), but we need (time, lat, lon)
# mhw_mask[i, j, t] -> should be (t, i, j)
mhw_transposed = mhw_mask.transpose(2, 0, 1).astype(np.uint8)  # (n_time, 60, 60)

# Create dataset
lat = region.latitude.values
lon = region.longitude.values
time_vals = target.time.values

out_ds = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_transposed)
    },
    coords={
        'time': time_vals,
        'lat': lat,
        'lon': lon
    }
)
out_ds.mhw.attrs['units'] = '1'
out_ds.mhw.attrs['long_name'] = 'marine heatwave mask (1=inside per-cell MHW)'

out_ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Written mhw_mask.nc")
print("Shape:", out_ds.mhw.shape)
print("Dtype:", out_ds.mhw.dtype)
