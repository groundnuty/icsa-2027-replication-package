
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
p = '/icsa2027_data_20261101T090944Z/s1z/sst_20080701.nc'
f = fs.open(p, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")
print(ds)
print("---- vars/coords ----")
print(ds.variables.keys())
print(ds.coords)
for v in ds.data_vars:
    a = ds[v].values
    print(v, a.dtype, a.shape, "min/max:", np.nanmin(a), np.nanmax(a))
f.close()
