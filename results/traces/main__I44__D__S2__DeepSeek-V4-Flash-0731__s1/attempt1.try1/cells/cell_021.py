
import xarray as xr
import numpy as np
import pandas as pd
import json
import os

# =====================================================
# SETUP
# =====================================================

# Load dataset
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Region bounds
lat_min, lat_max = 63.31, 64.51
lon_min, lon_max = 21.31, 22.51

# Get region indices
lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
lat_indices = np.where((lat_vals >= lat_min) & (lat_vals <= lat_max))[0]
lon_indices = np.where((lon_vals >= lon_min) & (lon_vals <= lon_max))[0]

region_lat = lat_vals[lat_indices].astype(np.float64)
region_lon = lon_vals[lon_indices].astype(np.float64)
n_lat = len(region_lat)
n_lon = len(region_lon)

print(f"Region: {n_lat} lat × {n_lon} lon")
print(f"Lat range: {region_lat[0]} to {region_lat[-1]}")
print(f"Lon range: {region_lon[0]} to {region_lon[-1]}")

# Target period
target_start = pd.Timestamp('2004-06-01')
target_end = pd.Timestamp('2004-08-31')
target_dates = pd.date_range(target_start, target_end, freq='D')

# Baseline data period (with windows)
data_start = pd.Timestamp('1991-12-27')
data_end = pd.Timestamp('2003-01-05')

# Get time indices
times = pd.DatetimeIndex(ds.time.values)
baseline_time_mask = (times >= data_start) & (times <= data_end)
baseline_time_idx = np.where(baseline_time_mask)[0]
target_time_mask = (times >= target_start) & (times <= target_end)
target_time_idx = np.where(target_time_mask)[0]

# Extract data
baseline_data = ds['analysed_sst'].isel(
    time=baseline_time_idx,
    latitude=slice(lat_indices[0], lat_indices[-1]+1),
    longitude=slice(lon_indices[0], lon_indices[-1]+1)
).values.astype(np.float64)

target_data = ds['analysed_sst'].isel(
    time=target_time_idx,
    latitude=slice(lat_indices[0], lat_indices[-1]+1),
    longitude=slice(lon_indices[0], lon_indices[-1]+1)
).values.astype(np.float64)

print(f"Baseline data: {baseline_data.shape}")
print(f"Target data: {target_data.shape}")

# Sea cells: finite on all target days
sea_cells = np.all(np.isfinite(target_data), axis=0)
print(f"Sea cells: {sea_cells.sum()} / {sea_cells.size}")
