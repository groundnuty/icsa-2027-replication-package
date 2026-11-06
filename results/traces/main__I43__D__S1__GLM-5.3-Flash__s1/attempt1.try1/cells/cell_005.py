import xarray as xr
ds = xr.open_dataset('/work/test/sst_20170601.nc', engine='h5netcdf')
print(ds)
print()
for v in ds.variables:
    print(v, ds[v].dtype, ds[v].shape, dict(ds[v].attrs))
print()
print('global attrs:', ds.attrs)
