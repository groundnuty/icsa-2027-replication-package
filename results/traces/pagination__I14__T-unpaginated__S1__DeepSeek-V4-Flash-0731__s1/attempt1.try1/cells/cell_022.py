
import numpy as np
import xarray as xr
import json
from datetime import date, timedelta

# Prepare output data

# Load per-cell MHW mask
per_cell_mhw = np.load('per_cell_mhw.npy')  # (92, 60, 60) bool
sea_mask = np.load('sea_mask.npy')

# Create output mask: 1 where cell is in per-cell MHW, 0 otherwise (including land cells)
mhw_mask = np.zeros(per_cell_mhw.shape, dtype=np.uint8)
mhw_mask[per_cell_mhw] = 1
# Ensure land cells are 0
for lat_i in range(60):
    for lon_i in range(60):
        if not sea_mask[lat_i, lon_i]:
            mhw_mask[:, lat_i, lon_i] = 0

print(f"MHW mask shape: {mhw_mask.shape}")
print(f"Non-zero count: {(mhw_mask > 0).sum()}")

# Load the coordinate values from a data file
import fsspec
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z/sst_20150601.nc'
f = fs.open(path, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")

# Get the region's coordinates
lat_vals = ds.latitude.values[132:192]
lon_vals = ds.longitude.values[436:496]
time_vals = ds.time.values

print(f"Latitude values: {lat_vals[:3]} ... {lat_vals[-3:]}")
print(f"Longitude values: {lon_vals[:3]} ... {lon_vals[-3:]}")
print(f"Time values: {time_vals}")

ds.close()
f.close()

# Target dates
target_dates = []
d = date(2015, 6, 1)
while d <= date(2015, 8, 31):
    target_dates.append(d)
    d += timedelta(days=1)

# Create time values as datetime64
time_vals_target = np.array(target_dates, dtype='datetime64[ns]')

print(f"Target time values: {time_vals_target[0]} to {time_vals_target[-1]}")

# Create the xarray dataset
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_mask)
    },
    coords={
        'time': time_vals_target,
        'lat': lat_vals,
        'lon': lon_vals
    }
)

ds_out['mhw'].attrs['units'] = '1'
ds_out['mhw'].attrs['long_name'] = 'marine heatwave mask'

# Write NetCDF
import os
os.makedirs('output', exist_ok=True)
ds_out.to_netcdf('output/mhw_mask.nc', engine='h5netcdf')
print("Written output/mhw_mask.nc")
