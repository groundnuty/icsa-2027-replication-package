import fsspec,xarray as xr
fs=fsspec.filesystem('onedata')
import os
os.makedirs('/work',exist_ok=True)
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','/work/s.nc')
d=xr.open_dataset('/work/s.nc',engine='h5netcdf');print(d)
t=d.time.values;print(t[0],t[-1],len(t))