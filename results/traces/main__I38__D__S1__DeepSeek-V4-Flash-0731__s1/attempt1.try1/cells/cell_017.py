import numpy as np
import pandas as pd
from datetime import date, timedelta
import xarray as xr

# ============================================================
# Load data
# ============================================================
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Region indices
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 60.49) & (lat <= 61.69))[0]
lon_idx = np.where((lon >= 17.25) & (lon <= 18.45))[0]
lat_region = lat[lat_idx]
lon_region = lon[lon_idx]

print(f"Region: {len(lat_region)} lat cells, {len(lon_region)} lon cells")

# Baseline data: 1991-12-27 to 2003-01-05
time = ds.time.values
baseline_start_idx = np.where(time == np.datetime64('1991-12-27'))[0][0]
baseline_end_idx = np.where(time == np.datetime64('2003-01-05'))[0][0]
print(f"Baseline indices: {baseline_start_idx} to {baseline_end_idx}")

# Target data: 2003-06-01 to 2003-08-31
target_start_idx = np.where(time == np.datetime64('2003-06-01'))[0][0]
target_end_idx = np.where(time == np.datetime64('2003-08-31'))[0][0]
print(f"Target indices: {target_start_idx} to {target_end_idx}")

# Read data for the region
baseline_data = ds.analysed_sst[baseline_start_idx:baseline_end_idx+1, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].values
target_data = ds.analysed_sst[target_start_idx:target_end_idx+1, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].values

print(f"Baseline data shape: {baseline_data.shape}")
print(f"Target data shape: {target_data.shape}")

# Generate baseline dates
baseline_dates = []
d = date(1991, 12, 27)
end_d = date(2003, 1, 5)
while d <= end_d:
    baseline_dates.append(d)
    d += timedelta(days=1)
print(f"Baseline dates: {len(baseline_dates)}")

# Generate target dates
target_dates = []
d = date(2003, 6, 1)
end_d = date(2003, 8, 31)
while d <= end_d:
    target_dates.append(d)
    d += timedelta(days=1)
print(f"Target dates: {len(target_dates)}")
print(f"Target dates: {target_dates[0]} to {target_dates[-1]}")
