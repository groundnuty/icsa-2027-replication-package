import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds)
print()
print('--- attrs ---')
for k, v in ds.attrs.items():
    print(k, ':', repr(v)[:300])
