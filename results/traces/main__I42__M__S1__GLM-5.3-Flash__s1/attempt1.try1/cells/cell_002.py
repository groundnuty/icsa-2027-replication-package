import xarray as xr
import numpy as np
p = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20120615.nc"
ds = xr.open_dataset(p, engine="h5netcdf")
print(ds)
print("\nattrs:", ds.attrs)
for v in ds.variables:
    var = ds[v]
    print(v, var.dims, var.shape, var.dtype, dict(list(var.attrs.items())[:6]) if var.attrs else "")
