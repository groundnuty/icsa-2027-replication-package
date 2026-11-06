import xarray as xr, numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
print(ds)
print()
for v in ds.variables:
    var = ds[v]
    print(v, var.dims, var.dtype, "chunks:", getattr(var.encoding.get("chunks"), None))
    a = getattr(var, "attrs", {})
    print("   attrs:", {k: a[k] for k in list(a)[:12]})
