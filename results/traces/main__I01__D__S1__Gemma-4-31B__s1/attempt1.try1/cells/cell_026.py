import fsspec
import os
import xarray as xr

fs = fsspec.filesystem('onedata')
s2_remote = 'icsa2027_data_20261101T090944Z/s2z/s2.nc'
s2_local = '/work/s2.nc'
fs.get(s2_remote, s2_local)
ds = xr.open_dataset(s2_local, engine="h5netcdf")
print(ds)
ds.close()
