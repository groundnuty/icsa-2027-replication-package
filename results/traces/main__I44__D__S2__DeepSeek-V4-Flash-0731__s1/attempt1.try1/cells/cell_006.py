
import xarray as xr
import numpy as np
import pandas as pd

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Get lat and lon indices for our region
lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
lat_indices = np.where((lat_vals >= 63.31) & (lat_vals <= 64.51))[0]
lon_indices = np.where((lon_vals >= 21.31) & (lon_vals <= 22.51))[0]

print(f"Lat indices: {lat_indices[0]} to {lat_indices[-1]}, {len(lat_indices)} cells")
print(f"Lon indices: {lon_indices[0]} to {lon_indices[-1]}, {len(lon_indices)} cells")

# Target period
target_start = np.datetime64('2004-06-01')
target_end = np.datetime64('2004-08-31')

# Baseline: 1992-01-01 to 2002-12-31, plus windows
baseline_start = np.datetime64('1991-12-27')  # 5 days before baseline start
baseline_end = np.datetime64('2003-01-05')    # 5 days after baseline end

# Get time indices
times = ds.time.values

# Find target indices
target_mask = (times >= target_start) & (times <= target_end)
target_idx = np.where(target_mask)[0]
print(f"\nTarget days: {len(target_idx)}")
print(f"Target start index: {target_idx[0]}, end index: {target_idx[-1]}")
print(f"Target dates: {times[target_idx[0]]} to {times[target_idx[-1]]}")

# Find baseline indices
baseline_mask = (times >= baseline_start) & (times <= baseline_end)
baseline_idx = np.where(baseline_mask)[0]
print(f"\nBaseline days: {len(baseline_idx)}")
print(f"Baseline start: {times[baseline_idx[0]]}, end: {times[baseline_idx[-1]]}")

# Extract target period data for the region
target_data = ds['analysed_sst'].isel(time=target_idx, latitude=slice(lat_indices[0], lat_indices[-1]+1), longitude=slice(lon_indices[0], lon_indices[-1]+1))
print(f"\nTarget data shape: {target_data.shape}")

# Check which cells are finite on all target days
finite_all = np.all(np.isfinite(target_data.values), axis=0)
print(f"Sea cells (finite all target days): {finite_all.sum()} out of {finite_all.size}")
