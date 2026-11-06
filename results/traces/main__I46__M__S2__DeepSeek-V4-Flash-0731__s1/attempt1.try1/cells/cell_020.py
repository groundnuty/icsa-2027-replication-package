
import xarray as xr
import numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

time = ds.time.values
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 64.39) & (lat <= 65.59))[0]
lon_idx = np.where((lon >= 23.41) & (lon <= 24.61))[0]

target_start = np.datetime64('2013-06-01')
target_end = np.datetime64('2013-08-31')
target_mask = (time >= target_start) & (time <= target_end)
target_time_idx = np.where(target_mask)[0]

region_lat = lat[lat_idx]
region_lon = lon[lon_idx]
target_time = time[target_time_idx]

print("region_lat:", region_lat[:3], "...", region_lat[-3:], "shape:", region_lat.shape)
print("region_lon:", region_lon[:3], "...", region_lon[-3:], "shape:", region_lon.shape)
print("target_time:", target_time[0], "to", target_time[-1], "shape:", target_time.shape)
