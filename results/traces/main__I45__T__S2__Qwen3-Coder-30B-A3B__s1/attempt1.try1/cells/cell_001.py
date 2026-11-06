import fsspec
import xarray as xr
import numpy as np

# Set up the filesystem
fs = fsspec.filesystem('onedata')

# Open the dataset
with fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    
print("Dataset dimensions:")
print(ds.dims)
print("\nDataset variables:")
print(ds.data_vars)
print("\nCoordinates:")
print(ds.coords)