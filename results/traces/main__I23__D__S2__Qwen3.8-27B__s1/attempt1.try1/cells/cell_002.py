import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds)
for name, v in ds.variables.items():
    print("VAR:", name, v.dims, v.dtype, v.shape)
