
import xarray as xr
import numpy as np
import datetime as dt

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91

lat_sel = ds.latitude.values
lon_sel = ds.longitude.values
lat_idx = np.where((lat_sel >= lat_min) & (lat_sel <= lon_max))[0]  # placeholder
lat_idx = np.where((lat_sel >= lat_min) & (lat_sel <= lat_max))[0]
lon_idx = np.where((lon_sel >= lon_min) & (lon_sel <= lon_max))[0]

time_vals = ds.time.values
target_start = np.datetime64('2019-06-01')
target_end = np.datetime64('2019-08-31')
target_idx = np.where((time_vals >= target_start) & (time_vals <= target_end))[0]

# Load only the target region & period data
sst = ds.analysed_sst.isel(time=target_idx, latitude=lat_idx, longitude=lon_idx).values
print("sst shape", sst.shape)
print("finite check", np.isfinite(sst).all())

# Get the time values for the target period
target_times = time_vals[target_idx]
print("first", target_times[0], "last", target_times[-1])
