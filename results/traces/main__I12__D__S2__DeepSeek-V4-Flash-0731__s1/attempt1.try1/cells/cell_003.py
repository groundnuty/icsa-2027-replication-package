
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds)
print(ds.dims)
print(list(ds.data_vars))
print(list(ds.coords))
