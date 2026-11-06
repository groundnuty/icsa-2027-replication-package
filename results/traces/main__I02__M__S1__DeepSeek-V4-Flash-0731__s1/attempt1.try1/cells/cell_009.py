
import numpy as np
import pandas as pd
from datetime import date, timedelta
import os
import xarray as xr

# Define the region
lat_min, lat_max = 54.17, 55.37
lon_min, lon_max = 13.25, 14.45

# Figure out the grid indices
ds = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20040101.nc', engine='h5netcdf')
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= lat_min) & (lat <= lat_max))[0]
lon_idx = np.where((lon >= lon_min) & (lon <= lon_max))[0]
print(f"Lat indices: {lat_idx[0]}..{lat_idx[-1]}, count={len(lat_idx)}")
print(f"Lon indices: {lon_idx[0]}..{lon_idx[-1]}, count={len(lon_idx)}")
ds.close()

# Now define all needed dates
baseline_start = date(1991, 12, 27)
baseline_end = date(2003, 1, 5)
target_start = date(2004, 6, 1)
target_end = date(2004, 8, 31)

# Generate all baseline dates
baseline_dates = []
d = baseline_start
while d <= baseline_end:
    baseline_dates.append(d)
    d += timedelta(days=1)

# Generate all target dates
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)

print(f"Baseline dates: {len(baseline_dates)} ({baseline_start} to {baseline_end})")
print(f"Target dates: {len(target_dates)} ({target_start} to {target_end})")
