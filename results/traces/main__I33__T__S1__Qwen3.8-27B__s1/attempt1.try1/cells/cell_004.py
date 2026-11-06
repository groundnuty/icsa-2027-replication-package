
import fsspec, xarray as xr, numpy as np, time
fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z'
p = f'{base}/sst_20140601.nc'
t0=time.time()
with fs.open(p, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
print("open+read time:", time.time()-t0)
print(ds)
