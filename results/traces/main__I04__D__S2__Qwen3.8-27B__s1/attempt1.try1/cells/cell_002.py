import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds)
print()
for k,v in ds.variables.items():
    print(k, v.dims, v.shape, v.dtype, dict(v.attrs))
print()
print('time coord: first', ds.time.values[:3], 'last', ds.time.values[-3:])
print('lat range', float(ds.lat.values.min()), float(ds.lat.values.max()))
print('lon range', float(ds.lon.values.min()), float(ds.lon.values.max()))
