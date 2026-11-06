
import xarray as xr
import numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

time = ds.time.values
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 64.39) & (lat <= 65.59))[0]
lon_idx = np.where((lon >= 23.41) & (lon <= 24.61))[0]

# Load target data again to check sea cells
target_start = np.datetime64('2013-06-01')
target_end = np.datetime64('2013-08-31')
target_mask = (time >= target_start) & (time <= target_end)
target_time_idx = np.where(target_mask)[0]
target_data = ds.analysed_sst.isel(time=target_time_idx, latitude=lat_idx, longitude=lon_idx).values

# Sea cell: finite on every target day
sea_mask = ~np.isnan(target_data).any(axis=0)
print("Sea cell count:", sea_mask.sum(), "out of", sea_mask.size)
print("Land cell count:", (~sea_mask).sum())
print("Sea cell indices (flattened):", np.where(sea_mask.flatten())[0])
