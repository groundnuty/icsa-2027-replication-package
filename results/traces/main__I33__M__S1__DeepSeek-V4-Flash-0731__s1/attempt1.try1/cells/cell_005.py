
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import os

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# Define region
lat_min, lat_max = 59.05, 60.25
lon_min, lon_max = 21.25, 22.45

# First, let's check a sample file for the region
ds = xr.open_dataset(f'{data_dir}/sst_20140601.nc', engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values
lat_mask = (lat >= lat_min) & (lat <= lat_max)
lon_mask = (lon >= lon_min) & (lon <= lon_max)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]

print(f"lat_idx: {lat_idx.min()}-{lat_idx.max()}")
print(f"lon_idx: {lon_idx.min()}-{lon_idx.max()}")
print(f"Number of lat: {len(lat_idx)}, number of lon: {len(lon_idx)}")

# Check the data for the region
sst_region = ds['analysed_sst'].isel(time=0, latitude=lat_idx, longitude=lon_idx).values
print(f"Shape: {sst_region.shape}")
print(f"SST values: {sst_region[:5,:5]}")
print(f"Finite: {np.isfinite(sst_region).sum()} out of {sst_region.size}")

ds.close()
