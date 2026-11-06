
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f=fs.open(p,'rb')
ds=xr.open_dataset(f,engine='h5netcdf')
print(ds)
print(ds.time.values[:3], ds.time.values[-3:], len(ds.time))
