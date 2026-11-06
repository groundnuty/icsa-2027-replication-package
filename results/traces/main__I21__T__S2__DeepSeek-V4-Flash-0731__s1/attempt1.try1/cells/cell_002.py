
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

f = fs.open(path, "rb")
ds = xr.open_dataset(f, engine="h5netcdf")

# Region: lat 57.33 to 58.53, lon 9.03 to 10.23
lat_min, lat_max = 57.33, 58.53
lon_min, lon_max = 9.03, 10.23

# Find indices
lats = ds.latitude.values
lons = ds.longitude.values

lat_indices = np.where((lats >= lat_min) & (lats <= lat_max))[0]
lon_indices = np.where((lons >= lon_min) & (lons <= lon_max))[0]

print(f"Lat indices: {lat_indices[0]} to {lat_indices[-1]}, count={len(lat_indices)}")
print(f"Lon indices: {lon_indices[0]} to {lon_indices[-1]}, count={len(lon_indices)}")
print(f"Lat values: {lats[lat_indices[0]]} to {lats[lat_indices[-1]]}")
print(f"Lon values: {lons[lon_indices[0]]} to {lons[lon_indices[-1]]}")

# Target period
target_start = np.datetime64('2021-06-01')
target_end = np.datetime64('2021-08-31')
target_idx = np.where((ds.time.values >= target_start) & (ds.time.values <= target_end))[0]
print(f"Target time indices: {target_idx[0]} to {target_idx[-1]}, count={len(target_idx)}")
print(f"Target dates: {ds.time.values[target_idx[0]]} to {ds.time.values[target_idx[-1]]}")

# Baseline period
base_start = np.datetime64('1992-01-01')
base_end = np.datetime64('2002-12-31')
base_idx = np.where((ds.time.values >= base_start) & (ds.time.values <= base_end))[0]
print(f"Baseline time indices: {base_idx[0]} to {base_idx[-1]}, count={len(base_idx)}")

# Check for days outside baseline but within ±5 days
ext_start = np.datetime64('1991-12-27')
ext_end = np.datetime64('2003-01-05')
ext_idx = np.where((ds.time.values >= ext_start) & (ds.time.values <= ext_end))[0]
print(f"Extended baseline time indices: {ext_idx[0]} to {ext_idx[-1]}, count={len(ext_idx)}")
