
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f=fs.open(p,'rb')
ds=xr.open_dataset(f,engine='h5netcdf')
print(ds)
for v in ds.variables: print(v, ds[v].dtype, ds[v].attrs)
