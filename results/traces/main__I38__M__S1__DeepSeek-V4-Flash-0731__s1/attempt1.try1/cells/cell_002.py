
import xarray as xr
import numpy as np

# Check a file from 2003
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20030601.nc', engine='h5netcdf')
print(ds)
print(ds.dims)
print(ds.coords)
