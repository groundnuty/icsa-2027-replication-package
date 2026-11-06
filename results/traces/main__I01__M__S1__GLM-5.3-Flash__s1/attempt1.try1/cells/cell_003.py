import xarray as xr
import numpy as np
p = '/data/icsa2027_data_20261101T090944Z/s1z/sst_20080601.nc'
ds = xr.open_dataset(p, engine='h5netcdf')
print(ds)
print()
for v in ds.variables:
    var = ds[v]
    print(v, var.dtype, var.shape, dict(var.attrs) if var.attrs else '')
print()
print('attrs:', ds.attrs)
