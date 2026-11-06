
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
f = fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_20150601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
for k, v in ds.variables.items():
    print(repr(k), v.dtype, v.shape)
ds.close()
