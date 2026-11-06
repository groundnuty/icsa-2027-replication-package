import xarray as xr
import numpy as np
import pandas as pd

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Region: lat 60.49-61.69, lon 17.25-18.45
lat = ds.latitude.values
lon = ds.longitude.values

lat_mask = (lat >= 60.49) & (lat <= 61.69)
lon_mask = (lon >= 17.25) & (lon <= 18.45)

lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]

print("Lat indices:", lat_idx[0], "to", lat_idx[-1], "count:", len(lat_idx))
print("Lat values:", lat[lat_idx[0]], "to", lat[lat_idx[-1]])
print("Lon indices:", lon_idx[0], "to", lon_idx[-1], "count:", len(lon_idx))
print("Lon values:", lon[lon_idx[0]], "to", lon[lon_idx[-1]])

# Time indices for baseline and target
time = ds.time.values

# Baseline: 1991-12-27 to 2003-01-05
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
baseline_mask = (time >= baseline_start) & (time <= baseline_end)
baseline_time_idx = np.where(baseline_mask)[0]
print("\nBaseline time indices:", baseline_time_idx[0], "to", baseline_time_idx[-1], "count:", len(baseline_time_idx))
print("Baseline dates:", time[baseline_time_idx[0]], "to", time[baseline_time_idx[-1]])

# Target: 2003-06-01 to 2003-08-31
target_start = np.datetime64('2003-06-01')
target_end = np.datetime64('2003-08-31')
target_mask = (time >= target_start) & (time <= target_end)
target_time_idx = np.where(target_mask)[0]
print("\nTarget time indices:", target_time_idx[0], "to", target_time_idx[-1], "count:", len(target_time_idx))
print("Target dates:", time[target_time_idx[0]], "to", time[target_time_idx[-1]])
