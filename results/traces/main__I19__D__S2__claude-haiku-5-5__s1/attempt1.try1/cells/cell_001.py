
import fsspec, os, xarray
os.makedirs('/work',exist_ok=True)
fs = fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
fs.get(p,'/work/sst_s2.nc')
ds=xarray.open_dataset('/work/sst_s2.nc',engine='h5netcdf')
print(ds)
for v in ds.variables: print(v, ds[v].attrs)
