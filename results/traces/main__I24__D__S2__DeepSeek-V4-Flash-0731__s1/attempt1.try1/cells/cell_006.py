
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds.time.values[:10])
print(ds.time.values[-5:])
print(ds.latitude.values[:10])
print(ds.latitude.values[-10:])
print(ds.longitude.values[:10])
print(ds.longitude.values[-10:])
