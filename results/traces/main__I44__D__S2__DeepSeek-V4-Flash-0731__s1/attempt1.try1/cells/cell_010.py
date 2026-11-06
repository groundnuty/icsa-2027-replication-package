
import xarray as xr
import numpy as np
import pandas as pd

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Get lat/lon indices
lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
lat_indices = np.where((lat_vals >= 63.31) & (lat_vals <= 64.51))[0]
lon_indices = np.where((lon_vals >= 21.31) & (lon_vals <= 22.51))[0]

# Region coordinates
region_lat = lat_vals[lat_indices]
region_lon = lon_vals[lon_indices]
print(f"Region: {len(region_lat)} lat × {len(region_lon)} lon = {len(region_lat)*len(region_lon)} cells")
print(f"Lat: {region_lat[0]} to {region_lat[-1]}")
print(f"Lon: {region_lon[0]} to {region_lon[-1]}")

# Target period
target_start = pd.Timestamp('2004-06-01')
target_end = pd.Timestamp('2004-08-31')
target_dates = pd.date_range(target_start, target_end, freq='D')
print(f"Target: {len(target_dates)} days")

# Extended baseline data period
data_start = pd.Timestamp('1991-12-27')
data_end = pd.Timestamp('2003-01-05')

# Find time indices in the dataset
times = pd.DatetimeIndex(ds.time.values)

# Baseline time indices
baseline_time_mask = (times >= data_start) & (times <= data_end)
baseline_time_idx = np.where(baseline_time_mask)[0]
print(f"Baseline time indices: {len(baseline_time_idx)} days")

# Target time indices
target_time_mask = (times >= target_start) & (times <= target_end)
target_time_idx = np.where(target_time_mask)[0]
print(f"Target time indices: {len(target_time_idx)} days")

# Extract baseline data for region
print("\nExtracting baseline data...")
baseline_data = ds['analysed_sst'].isel(
    time=baseline_time_idx,
    latitude=slice(lat_indices[0], lat_indices[-1]+1),
    longitude=slice(lon_indices[0], lon_indices[-1]+1)
).values.astype(np.float64)
print(f"Baseline data shape: {baseline_data.shape}")

# Extract target data for region
print("Extracting target data...")
target_data = ds['analysed_sst'].isel(
    time=target_time_idx,
    latitude=slice(lat_indices[0], lat_indices[-1]+1),
    longitude=slice(lon_indices[0], lon_indices[-1]+1)
).values.astype(np.float64)
print(f"Target data shape: {target_data.shape}")

# Identify sea cells (finite on all target days)
sea_cells = np.all(np.isfinite(target_data), axis=0)
print(f"Sea cells: {sea_cells.sum()}")

# Save for later
np.save('/work/baseline_data.npy', baseline_data)
np.save('/work/target_data.npy', target_data)
np.save('/work/sea_cells.npy', sea_cells)
np.save('/work/region_lat.npy', region_lat)
np.save('/work/region_lon.npy', region_lon)
print("Data saved.")
