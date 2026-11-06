import xarray as xr
d=xr.open_dataset('/work/sst_20190601.nc',engine='h5netcdf')
print(d)
print(d.lat.values[:5], d.lon.values[:5])