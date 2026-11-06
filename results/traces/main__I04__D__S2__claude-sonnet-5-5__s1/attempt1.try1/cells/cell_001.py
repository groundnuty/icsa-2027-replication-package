
import fsspec,xarray as xr,numpy as np
fs=fsspec.filesystem('onedata')
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','/work/s.nc')
ds=xr.open_dataset('/work/s.nc',engine='h5netcdf')
print(ds)
for v in ds.data_vars:print(v,ds[v].attrs)
print(ds.time.values[[0,-1]],ds.lat.values[[0,-1]],ds.lon.values[[0,-1]])
