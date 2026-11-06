import fsspec, time, xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')
root = 'icsa2027_data_20261101T090944Z/s1z'
t0 = time.time()
with fs.open(root+'/sst_20090601.nc','rb') as f:
    ds = xarray.open_dataset(f, engine='h5netcdf')
print('read time:', time.time()-t0)
print(ds)