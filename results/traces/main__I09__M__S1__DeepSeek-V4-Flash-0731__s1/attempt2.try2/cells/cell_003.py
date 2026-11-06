
import xarray as xr
import numpy as np

# Open one file to understand structure
f = '/data/icsa2027_data_20261101T090944Z/s1z/sst_20220601.nc'
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
print(ds.variables)
