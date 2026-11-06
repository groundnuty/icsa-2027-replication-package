
import fsspec,xarray as xr
fs=fsspec.filesystem('onedata')
import os
os.makedirs('/work',exist_ok=True)
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','/work/s.nc')
ds=xr.open_dataset('/work/s.nc',engine='h5netcdf')
print(ds)
print(ds.time.values[[0,-1]])
