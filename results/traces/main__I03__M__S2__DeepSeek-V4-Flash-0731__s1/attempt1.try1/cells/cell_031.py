
import xarray as xr
import numpy as np
import os

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

lat_idx = list(range(34, 94))
lon_idx = list(range(213, 273))

time = ds['time'].values
target_time_idx = np.load('/tmp/target_time_idx.npy')

# Get coordinate values
region_lat = ds['latitude'].values[lat_idx]
region_lon = ds['longitude'].values[lon_idx]
region_time = time[target_time_idx]

print("Lat:", region_lat[0], "to", region_lat[-1], "count:", len(region_lat))
print("Lon:", region_lon[0], "to", region_lon[-1], "count:", len(region_lon))
print("Time:", region_time[0], "to", region_time[-1], "count:", len(region_time))

# MHW mask
mhw_mask = np.load('/tmp/mhw_mask_correct.npy')
print("MHW mask shape:", mhw_mask.shape)
print("MHW mask dtype:", mhw_mask.dtype)
