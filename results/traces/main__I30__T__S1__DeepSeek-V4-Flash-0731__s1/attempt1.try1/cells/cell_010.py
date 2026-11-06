
import xarray as xr
import fsspec
import numpy as np
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Get coordinate info first
lat = ds.latitude.values
lon = ds.longitude.values
time = ds.time.values
print("lat range:", lat.min(), lat.max(), "n:", len(lat))
print("lon range:", lon.min(), lon.max(), "n:", len(lon))
print("time range:", time[0], time[-1], "n:", len(time))
