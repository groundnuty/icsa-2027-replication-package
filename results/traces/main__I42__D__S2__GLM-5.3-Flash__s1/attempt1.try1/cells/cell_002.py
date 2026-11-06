import xarray as xr, time
t0=time.time()
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print("open took", time.time()-t0, "s")
print(ds)
print()
for v in ds.variables:
    print(v, ds[v].dtype, ds[v].shape)
