import fsspec, os, xarray as xr
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/work/sst',exist_ok=True)
fs.get(f'{base}/sst_20140601.nc','/work/sst/sst_20140601.nc')
print(os.path.getsize('/work/sst/sst_20140601.nc'))
ds=xr.open_dataset('/work/sst/sst_20140601.nc',engine='h5netcdf')
print(ds)
for v in ds.variables: print(v, ds[v].attrs)