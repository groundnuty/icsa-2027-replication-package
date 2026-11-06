
import numpy as np
import xarray as xr
import json
import os
from datetime import date, timedelta

# Load data
mhw_mask = np.load('/work/mhw_mask.npy')  # (92, 60, 60) uint8
tgt_time = np.load('/work/tgt_time.npy')
lat_vals = np.load('/work/lat_vals.npy')
lon_vals = np.load('/work/lon_vals.npy')

# Reconstruct target dates
target_dates = [date(1970,1,1) + timedelta(days=int(t)) for t in tgt_time]

# Create output directory
os.makedirs('output', exist_ok=True)

# Create xarray dataset for mhw_mask
# Use the dataset's coordinate values (datetime64 for time, float32 for lat/lon)
time_coords = np.array([np.datetime64(d.isoformat()) for d in target_dates], dtype='datetime64[ns]')
lat_coords = lat_vals.astype('float32')
lon_coords = lon_vals.astype('float32')

ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask.astype('uint8'))
    },
    coords={
        'time': time_coords,
        'lat': lat_coords,
        'lon': lon_coords,
    }
)

# Write to NetCDF
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Wrote output/mhw_mask.nc")
print(ds_out)
print("mhw dtype:", ds_out.mhw.dtype)
print("mhw shape:", ds_out.mhw.shape)
print("mhw values:", np.unique(ds_out.mhw.values))
