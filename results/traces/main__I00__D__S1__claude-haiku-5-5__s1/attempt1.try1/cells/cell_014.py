import xarray as xr
d=xr.open_dataset('/work/output/mhw_mask.nc',engine='h5netcdf')
print(d); print(d.mhw.dtype)