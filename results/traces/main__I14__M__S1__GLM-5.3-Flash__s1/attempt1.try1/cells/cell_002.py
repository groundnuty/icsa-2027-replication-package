import os, xarray as xr, numpy as np
d = "/data/icsa2027_data_20261101T090944Z/s1z"
p = os.path.join(d, "sst_20150601.nc")
ds = xr.open_dataset(p, engine="h5netcdf")
print(ds)
print()
for v in ds.variables:
    var = ds[v]
    print(v, var.dtype, var.shape, dict(var.attrs))
print()
print("global attrs:", ds.attrs)
