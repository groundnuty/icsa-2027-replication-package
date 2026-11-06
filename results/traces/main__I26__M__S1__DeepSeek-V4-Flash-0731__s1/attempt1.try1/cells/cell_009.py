
import xarray as xr
import numpy as np
import os
import datetime

# Define paths
data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# Region
lat_min, lat_max = 57.83, 59.03
lon_min, lon_max = 17.41, 18.61

# Target period
target_start = datetime.date(2007, 6, 1)
target_end = datetime.date(2007, 8, 31)

# Build list of target dates
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += datetime.timedelta(days=1)
print(f"Target dates: {len(target_dates)} days, from {target_dates[0]} to {target_dates[-1]}")

# Load one file to get grid and indices
path = os.path.join(data_dir, f"sst_{target_dates[0].strftime('%Y%m%d')}.nc")
ds = xr.open_dataset(path, engine='h5netcdf')
lat = ds['latitude'].values
lon = ds['longitude'].values
lat_idx = np.where((lat >= lat_min) & (lat <= lat_max))[0]
lon_idx = np.where((lon >= lon_min) & (lon <= lon_max))[0]
ds.close()

# Load target data
target_sst = np.full((len(target_dates), len(lat_idx), len(lon_idx)), np.nan, dtype=np.float64)
for i, date in enumerate(target_dates):
    fname = f"sst_{date.strftime('%Y%m%d')}.nc"
    path = os.path.join(data_dir, fname)
    ds = xr.open_dataset(path, engine='h5netcdf')
    # Select the region
    sst_region = ds['analysed_sst'].isel(time=0, latitude=lat_idx, longitude=lon_idx).values
    target_sst[i] = sst_region.astype(np.float64)
    ds.close()

print(f"Target SST shape: {target_sst.shape}")
print(f"NaN count: {np.isnan(target_sst).sum()}")
print(f"Finite count: {np.isfinite(target_sst).sum()}")

# Identify sea cells: finite on every target day
sea_cells = np.all(np.isfinite(target_sst), axis=0)
print(f"Sea cells: {sea_cells.sum()} out of {sea_cells.size}")

# Save for later
np.save('target_sst.npy', target_sst)
np.save('sea_cells.npy', sea_cells)
np.save('lat_idx.npy', lat_idx)
np.save('lon_idx.npy', lon_idx)
