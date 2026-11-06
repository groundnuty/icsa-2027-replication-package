
import xarray as xr
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20090601.nc', engine='h5netcdf')
print(ds)
print(ds.variables)
