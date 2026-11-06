import xarray as xr
import numpy as np
ds = xr.open_dataset('/work/data/sst_19830101.nc', engine="h5netcdf")
print(ds)
print("attrs:", dict(ds.attrs))
for v in ds.variables:
    var = ds[v]
    print(v, var.dims, var.shape, var.dtype)
    for k,val in var.attrs.items():
        print("   ", k, "=", str(val)[:100])