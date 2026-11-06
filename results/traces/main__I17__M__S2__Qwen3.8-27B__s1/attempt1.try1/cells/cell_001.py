
import xarray as xr
import numpy as np
path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")
print(ds)
print("---- coords ----")
for k, v in ds.coords.items():
    print(k, v.dtype, v.shape, "attrs:", dict(v.attrs))
    vals = v.values
    print("  first/last:", vals[:3], vals[-3:])
