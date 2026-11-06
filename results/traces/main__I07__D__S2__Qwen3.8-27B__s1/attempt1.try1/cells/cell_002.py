import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds)
print('---')
print(ds.encoding)
print('---')
for v in ds.variables:
    var = ds[v]
    print(v, var.dims, var.shape, var.dtype)
