import fsspec,xarray as xr
fs=fsspec.filesystem('onedata')
fs.get('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc','/work/s.nc')
d=xr.open_dataset('/work/s.nc',engine='h5netcdf');print(d)
print(d.time.values[[0,-1]],d.lat.values[[0,-1]],d.lon.values[[0,-1]])