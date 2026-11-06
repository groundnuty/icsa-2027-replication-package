
import xarray as xr
import numpy as np
from datetime import date, timedelta
import os

# Check what files exist
data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# First, check the exact coordinate values at region bounds
ds = xr.open_dataset(f'{data_dir}/sst_20030601.nc', engine='h5netcdf')
lats = ds.latitude.values
lons = ds.longitude.values
ds.close()

lat_indices = np.where((lats >= 60.49) & (lats <= 61.69))[0]
lon_indices = np.where((lons >= 17.25) & (lons <= 18.45))[0]
print(f"Region: lat {lats[lat_indices[0]]} to {lats[lat_indices[-1]]}, {len(lat_indices)} cells")
print(f"Region: lon {lons[lon_indices[0]]} to {lons[lon_indices[-1]]}, {len(lon_indices)} cells")

# Check if there are any other coordinate variables or masks we need
print(ds)
print(list(ds.data_vars))
print(list(ds.coords))
