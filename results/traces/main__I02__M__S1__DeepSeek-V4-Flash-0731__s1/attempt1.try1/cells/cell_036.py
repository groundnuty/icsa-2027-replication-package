
import xarray as xr
import numpy as np
import os
from datetime import date, timedelta
import json

# Get coordinate values from the dataset
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20040601.nc', engine='h5netcdf')
lat_vals = ds.latitude.values[34:94]  # Region lat values
lon_vals = ds.longitude.values[213:273]  # Region lon values
ds.close()

print(f"Lat values: {lat_vals}")
print(f"Lon values: {lon_vals}")
print(f"Lat shape: {lat_vals.shape}, Lon shape: {lon_vals.shape}")
