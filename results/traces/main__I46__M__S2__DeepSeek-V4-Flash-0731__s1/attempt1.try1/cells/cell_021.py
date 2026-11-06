
import xarray as xr
import numpy as np
import json
import os

# Load the data
hot = np.load('/tmp/hot.npy')
sea_mask = np.load('/tmp/sea_mask.npy')
mhw_mask = np.load('/tmp/mhw_mask.npy')  # This is the per-cell MHW mask

print("hot shape:", hot.shape)
print("mhw_mask shape:", mhw_mask.shape)
print("mhw_mask dtype:", mhw_mask.dtype)

# Actually, I computed mhw_mask in a previous cell but didn't save it.
# Let me recompute it here.

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

time = ds.time.values
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 64.39) & (lat <= 65.59))[0]
lon_idx = np.where((lon >= 23.41) & (lon <= 24.61))[0]

region_lat = lat[lat_idx]
region_lon = lon[lon_idx]

target_start = np.datetime64('2013-06-01')
target_end = np.datetime64('2013-08-31')
target_mask = (time >= target_start) & (time <= target_end)
target_time_idx = np.where(target_mask)[0]
target_time = time[target_time_idx]

n_target = len(target_time_idx)
n_lat = len(lat_idx)
n_lon = len(lon_idx)

print("n_target:", n_target, "n_lat:", n_lat, "n_lon:", n_lon)
