import numpy as np
import json
import os
import xarray as xr
from datetime import datetime, timedelta
import h5py

# Load data
cell_mhw_mask = np.load('/work/cell_mhw_mask.npy')  # (92, 60, 60) bool

# Read coordinates from original file
f = h5py.File('/work/sst_s2.nc', 'r')
region_lats = f['latitude'][217:277].astype(np.float32)
region_lons = f['longitude'][421:481].astype(np.float32)

time_raw = f['time'][9282:9374]
epoch = datetime(1981, 1, 1)
target_dates = [epoch + timedelta(seconds=int(t)) for t in time_raw]
time_vals = np.array([np.datetime64(dt.isoformat()) for dt in target_dates])

# Create the mhw_mask dataset
mhw_uint8 = cell_mhw_mask.astype(np.uint8)

ds = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_uint8)
    },
    coords={
        'time': time_vals,
        'lat': region_lats,
        'lon': region_lons
    }
)

# Set attributes for mhw variable
ds['mhw'].attrs['long_name'] = 'Marine heatwave mask'
ds['mhw'].attrs['units'] = '1'
ds['mhw'].attrs['description'] = '1 if cell is inside a per-cell marine heatwave on that day, 0 otherwise'

# Write to file
ds.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc written")

# Verify by reading back
ds_check = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("Shape:", ds_check.mhw.shape)
print("Dtype:", ds_check.mhw.dtype)
print("Time range:", ds_check.time.values[0], "to", ds_check.time.values[-1])
print("Lat range:", ds_check.lat.values[0], "to", ds_check.lat.values[-1])
print("Lon range:", ds_check.lon.values[0], "to", ds_check.lon.values[-1])
print("Sum of mhw:", ds_check.mhw.sum().values)
