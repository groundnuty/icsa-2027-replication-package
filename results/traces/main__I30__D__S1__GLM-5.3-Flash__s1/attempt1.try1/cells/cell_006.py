import xarray as xr, h5netcdf, time
t0=time.time()
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds)
print('open time', time.time()-t0)
