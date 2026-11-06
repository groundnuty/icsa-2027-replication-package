
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
sst_region = ds.analysed_sst.sel(latitude=slice(57.83, 59.03), longitude=slice(17.41, 18.61))
target = sst_region.sel(time=slice('2008-06-01', '2008-08-31'))

print("Latitudes:", target.latitude.values)
print("Longitudes:", target.longitude.values)
print("Times:", target.time.values)
print("Shapes:", target.latitude.shape, target.longitude.shape, target.time.shape)
