import xarray as xr
ds=xr.open_dataset(d+'/sst_20050601.nc',engine='h5netcdf');print(ds)
print(ds.lat.values[:3] if 'lat' in ds else '')