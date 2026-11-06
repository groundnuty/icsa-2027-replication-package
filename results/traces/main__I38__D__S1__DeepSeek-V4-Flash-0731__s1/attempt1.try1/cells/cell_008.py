import fsspec
fs = fsspec.filesystem('onedata')
# Download s2 file
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', '/work/sst_s2.nc')
print("Downloaded s2")

# Download one s1 file
fs.get('icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc', '/work/sst_19820101.nc')
print("Downloaded s1 example")

import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds)
print("---")
ds2 = xr.open_dataset('/work/sst_19820101.nc', engine='h5netcdf')
print(ds2)
