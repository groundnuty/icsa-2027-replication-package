
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Select region
lat_sel = ds.latitude[(ds.latitude >= 57.83) & (ds.latitude <= 59.03)]
lon_sel = ds.longitude[(ds.longitude >= 17.41) & (ds.longitude <= 18.61)]
print("lat:", lat_sel.values)
print("lon:", lon_sel.values)
print("nlat:", len(lat_sel), "nlon:", len(lon_sel))

# Check time range
print(ds.time.values[0], ds.time.values[-1])
