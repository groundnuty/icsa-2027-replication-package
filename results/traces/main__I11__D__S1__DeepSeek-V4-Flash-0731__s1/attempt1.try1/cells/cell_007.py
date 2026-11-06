
import fsspec
fs = fsspec.filesystem('onedata')
# Download one file to inspect
fs.get('icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc', '/work/sst_19820101.nc')
print("Downloaded")

import xarray as xr
ds = xr.open_dataset('/work/sst_19820101.nc', engine='h5netcdf')
print(ds)
