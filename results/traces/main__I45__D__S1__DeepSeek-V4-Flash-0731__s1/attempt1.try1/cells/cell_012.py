
import xarray as xr
import numpy as np
from datetime import datetime, timedelta

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Find indices for our region
lat_idx = np.where((ds['latitude'].values >= 63.31) & (ds['latitude'].values <= 64.51))[0]
lon_idx = np.where((ds['longitude'].values >= 21.31) & (ds['longitude'].values <= 22.51))[0]

# Time indices for baseline (1992-01-01 to 2002-12-31) plus the 5-day extensions
# Extension: 1991-12-27 to 1991-12-31 and 2003-01-01 to 2003-01-05
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')

# Target period
target_start = np.datetime64('2009-06-01')
target_end = np.datetime64('2009-08-31')

# Get all time values
times = ds['time'].values

# Find indices
base_idx = np.where((times >= baseline_start) & (times <= baseline_end))[0]
target_idx = np.where((times >= target_start) & (times <= target_end))[0]

print("Baseline indices:", base_idx[0], "to", base_idx[-1], "count:", len(base_idx))
print("Target indices:", target_idx[0], "to", target_idx[-1], "count:", len(target_idx))

# Extract the data
# Region: 60 lat x 60 lon = 3600 cells
# Baseline: about 4018 days
# Target: 92 days

# Load baseline data for the region
base_sst = ds['analysed_sst'].isel(time=base_idx, latitude=lat_idx, longitude=lon_idx).values
print("Baseline shape:", base_sst.shape)

# Load target data
target_sst = ds['analysed_sst'].isel(time=target_idx, latitude=lat_idx, longitude=lon_idx).values
print("Target shape:", target_sst.shape)

# Also save the coordinates
region_lats = ds['latitude'].values[lat_idx]
region_lons = ds['longitude'].values[lon_idx]
base_times = times[base_idx]
target_times = times[target_idx]

# Save to files for later use
np.save('/work/base_sst.npy', base_sst)
np.save('/work/target_sst.npy', target_sst)
np.save('/work/region_lats.npy', region_lats)
np.save('/work/region_lons.npy', region_lons)
np.save('/work/base_times.npy', base_times)
np.save('/work/target_times.npy', target_times)

print("Saved successfully")
ds.close()
