
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
f = fs.open('/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xarray.open_dataset(f, engine='h5netcdf')
print(ds)
print("---")
for v in ds.variables:
    print(v, ds[v].dims, ds[v].dtype)
ds.close()
