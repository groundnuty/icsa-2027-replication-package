import xarray as xr
import os

# Open one file to check its content
sample_file = '/data/icsa2027_data_20261101T090944Z/s1z/sst_20231231.nc'
ds = xr.open_dataset(sample_file, engine="h5netcdf")
print(ds)
