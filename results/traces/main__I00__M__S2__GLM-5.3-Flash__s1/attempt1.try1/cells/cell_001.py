import xarray as xr, numpy as np, pandas as pd

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

print("DIMS:")
for k, v in ds.sizes.items():
    print(" ", k, v)
print("\nVARS:")
for name, var in ds.variables.items():
    attrs = {a: var.attrs[a] for a in var.attrs}
    print(f"  {name}: dims={var.dims}, dtype={var.dtype}, attrs={attrs}")
print("\nGLOBAL ATTRS:", dict(ds.attrs))
