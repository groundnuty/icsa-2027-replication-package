
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
p = '/icsa2027_data_20261101T090944Z/s1z/sst_20080701.nc'
print("size:", fs.size(p))
f = fs.open(p, "rb")
ds = xarray.open_dataset(f, engine="h5netcdf")
print(ds)
f.close()
