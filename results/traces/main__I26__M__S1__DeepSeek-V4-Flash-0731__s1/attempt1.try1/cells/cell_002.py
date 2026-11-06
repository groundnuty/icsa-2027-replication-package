
import xarray as xr
import numpy as np

# Check the structure of one file
path = '/data/icsa2027_data_20261101T090944Z/s1z/sst_20230601.nc'
ds = xr.open_dataset(path, engine='h5netcdf')
print(ds)
