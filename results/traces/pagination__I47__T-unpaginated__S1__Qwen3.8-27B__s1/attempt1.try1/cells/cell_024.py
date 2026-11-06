
import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
f = fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_20190601.nc', 'rb')
ds = xr.open_dataset(f, engine="h5netcdf")
t = ds['time'].values
print(repr(t), t.dtype)
print("unit attribute:", ds['time'].attrs)
ds.close(); f.close()
