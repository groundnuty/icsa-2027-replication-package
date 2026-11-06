
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Select region
lat_sel = ds.latitude[(ds.latitude >= 55.67) & (ds.latitude <= 56.87)]
lon_sel = ds.longitude[(ds.longitude >= 16.45) & (ds.longitude <= 17.65)]
print("lat range:", lat_sel.min().values, lat_sel.max().values, "n=", len(lat_sel))
print("lon range:", lon_sel.min().values, lon_sel.max().values, "n=", len(lon_sel))
print(ds.time.values[0], ds.time.values[-1])
