
import os
import h5py
import numpy as np

base_dir = '/data/icsa2027_data_20261101T090944Z/s1z'
f0 = os.path.join(base_dir, 'sst_20030601.nc')

with h5py.File(f0, 'r') as h5:
    lat = h5['latitude'][:]
    lon = h5['longitude'][:]

lat_idx = np.where((lat >= 60.09) & (lat <= 61.29))[0]
lon_idx = np.where((lon >= 20.01) & (lon <= 21.21))[0]

lat_region = lat[lat_idx]
lon_region = lon[lon_idx]

print(f"lat_region shape: {lat_region.shape}")
print(f"lat_region: {lat_region}")
print(f"lon_region shape: {lon_region.shape}")
print(f"lon_region: {lon_region}")
print(f"lat_region dtype: {lat_region.dtype}")
print(f"lon_region dtype: {lon_region.dtype}")

# Also check time dimension
with h5py.File(f0, 'r') as h5:
    time_vals = h5['time'][:]
print(f"time values: {time_vals}")

# Check if there's a time coordinate in the netCDF files
import xarray as xr
ds = xr.open_dataset(f0, engine='h5netcdf')
print(f"\nDataset coordinates:")
print(ds.coords)
print(f"time values: {ds.time.values}")
print(f"time dtype: {ds.time.dtype}")
ds.close()
