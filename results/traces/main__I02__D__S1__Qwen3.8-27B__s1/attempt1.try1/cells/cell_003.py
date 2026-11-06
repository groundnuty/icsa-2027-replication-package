import fsspec, os
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/data', exist_ok=True)
fs.get(os.path.join(base,'sst_19920101.nc'), '/work/data/sst_19920101.nc')
fs.get(os.path.join(base,'sst_20040601.nc'), '/work/data/sst_20040601.nc')
print(os.path.getsize('/work/data/sst_19920101.nc'))

import xarray as xr
ds = xr.open_dataset('/work/data/sst_19920101.nc', engine='h5netcdf')
print(ds)
print({k: (v.dtype, v.shape) for k,v in ds.variables.items()})
