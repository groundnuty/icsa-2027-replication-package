
import fsspec, xarray as xr
fs = fsspec.filesystem('onedata')
f = fs.open('/icsa2027_data_20261101T090944Z/s1z/sst_20100601.nc', 'rb')
ds = xarray.open_dataset(f, engine='h5netcdf')
print(ds)
for name, var in ds.variables.items():
    print(name, var.dims, var.dtype)
    for k,v in var.attrs.items():
        print('   ', k, '=', v)
print('---')
print('lat:', ds.lat.values)
print('lon:', ds.lon.values)
ds.close()
