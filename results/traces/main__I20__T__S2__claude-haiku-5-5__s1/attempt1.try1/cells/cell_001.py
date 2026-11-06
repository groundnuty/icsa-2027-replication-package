
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
path='icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f=fs.open(path,'rb')
ds=xr.open_dataset(f,engine='h5netcdf')
print(ds)
