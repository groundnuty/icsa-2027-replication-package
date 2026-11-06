import xarray as xr
x=xr.open_dataset('/work/d/sst_20050601.nc',engine='h5netcdf');print(x)
y=xr.open_dataset('/work/d/sst_19920101.nc',engine='h5netcdf');print(y.time.values, list(y.data_vars))