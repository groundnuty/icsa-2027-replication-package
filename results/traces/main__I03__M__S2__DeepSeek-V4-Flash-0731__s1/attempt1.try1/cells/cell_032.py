
import xarray as xr
import numpy as np
import json
import os
from datetime import date as dt_date

os.makedirs('output', exist_ok=True)

# Load data
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

lat_idx = list(range(34, 94))
lon_idx = list(range(213, 273))
time = ds['time'].values
target_time_idx = np.load('/tmp/target_time_idx.npy')
mhw_mask = np.load('/tmp/mhw_mask_correct.npy')

# Create the output NetCDF
region_lat = ds['latitude'].values[lat_idx]
region_lon = ds['longitude'].values[lon_idx]
region_time = time[target_time_idx]

# Create dataset
out_ds = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': region_time,
        'lat': region_lat,
        'lon': region_lon,
    }
)
out_ds['mhw'].attrs['long_name'] = 'marine heatwave mask'
out_ds['mhw'].attrs['units'] = '1 = inside MHW, 0 = outside'

# Write NetCDF
out_ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Wrote output/mhw_mask.nc")

# Verify
check_ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("Verify: shape:", check_ds['mhw'].shape, "dtype:", check_ds['mhw'].dtype)
print("Verify: time:", check_ds['time'].values[0], "to", check_ds['time'].values[-1])
print("Verify: lat:", check_ds['lat'].values[0], "to", check_ds['lat'].values[-1])
print("Verify: lon:", check_ds['lon'].values[0], "to", check_ds['lon'].values[-1])
print("Verify: sum:", int(check_ds['mhw'].sum()))
