
import fsspec, xarray as xr
fs = fsspec.filesystem('onedata')
base = '/icsa2027_data_20261101T090944Z/s1z/'
f = fs.open(base + 'sst_20080601.nc', 'rb')
ds = xarray.open_dataset(f, engine='h5netcdf')
print(ds)
print('---')
for v in ds.variables:
    print(v, ds[v].dtype)
ds.close()
