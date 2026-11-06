
import xarray as xr
import numpy as np

# Open one file to understand the structure
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20040101.nc', engine='h5netcdf')
print(ds)
print(ds.variables)
