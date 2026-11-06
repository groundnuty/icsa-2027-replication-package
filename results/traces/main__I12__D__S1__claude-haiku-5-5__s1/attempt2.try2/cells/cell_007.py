import fsspec,xarray as xr,os
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
os.makedirs('/work',exist_ok=True)
fs.get(base+'sst_20090601.nc','/work/test.nc')
print(os.path.getsize('/work/test.nc'))
ds=xr.open_dataset('/work/test.nc',engine='h5netcdf')
print(ds)
for v in ds.variables: print(v, ds[v].attrs)