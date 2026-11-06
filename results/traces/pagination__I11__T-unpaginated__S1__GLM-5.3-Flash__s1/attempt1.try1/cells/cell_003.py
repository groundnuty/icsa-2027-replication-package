import fsspec, xarray as xr
fs = fsspec.filesystem('onedata')
p = 'icsa2027_data_20261101T090944Z/s1z'
f = fs.open(p + '/sst_20210601.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
print(ds)
print('---')
for v in ds.variables:
    print(v, ds[v].dtype, ds[v].shape, dict(ds[v].attrs))
print('global attrs:', dict(ds.attrs))
