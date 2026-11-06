import fsspec, os
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/data', exist_ok=True)
fs.get(base + '/sst_19911227.nc', '/work/data/sst_19911227.nc')
import xarray as xr
ds = xr.open_dataset('/work/data/sst_19911227.nc', engine='h5netcdf')
print(ds)
print("---attrs---")
for k,v in ds.attrs.items(): print(k, repr(v)[:200])
import numpy as np
print(ds.variables.keys())
print({k: (str(v.dtype), v.shape) for k,v in ds.variables.items()})
print("size on disk:", os.path.getsize('/work/data/sst_19911227.nc'))
