
import fsspec
fs = fsspec.filesystem('onedata')
# Download s2z file
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', '/work/sst_s2.nc')
print("Downloaded")

import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds)
print("\nTime range:")
print(ds.time.min().values, ds.time.max().values)
print("\nTime count:", ds.time.shape)
