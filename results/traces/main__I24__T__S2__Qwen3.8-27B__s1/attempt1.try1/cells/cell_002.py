import fsspec, xarray as xr, numpy as np
print("numpy", np.__version__, "xarray", xr.__version__)
fs = fsspec.filesystem('onedata')
p = "icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
f = fs.open(p, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
print(ds)
print("---- attrs time ----")
print(ds.time.attrs if "time" in ds else None)
for v in ds.variables:
    var = ds[v]
    print(v, var.dims, var.shape, var.dtype, dict(var.attrs))
