
import xarray as xr
import numpy as np
from datetime import date, timedelta
import os

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# First, let's read one file to get lat/lon indices
f0 = os.path.join(data_dir, 'sst_20220601.nc')
ds0 = xr.open_dataset(f0, engine='h5netcdf')
lats = ds0.latitude.values
lons = ds0.longitude.values
lat_idx = np.where((lats >= 54.81) & (lats <= 56.01))[0]
lon_idx = np.where((lons >= 19.61) & (lons <= 20.81))[0]
ds0.close()

print(f"Lat indices: {lat_idx[0]} to {lat_idx[-1]}, count={len(lat_idx)}")
print(f"Lon indices: {lon_idx[0]} to {lon_idx[-1]}, count={len(lon_idx)}")

# Load all target data
target_dates = []
d = target_start = date(2022, 6, 1)
target_end = date(2022, 8, 31)
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)

print(f"Target dates: {len(target_dates)} days from {target_dates[0]} to {target_dates[-1]}")

# Load target SST for the region
target_sst = np.zeros((len(target_dates), len(lat_idx), len(lon_idx)), dtype=np.float64)
for i, d in enumerate(target_dates):
    fname = f"sst_{d.strftime('%Y%m%d')}.nc"
    fpath = os.path.join(data_dir, fname)
    ds = xr.open_dataset(fpath, engine='h5netcdf')
    target_sst[i] = ds.analysed_sst[0, lat_idx[0]:lat_idx[-1]+1, lon_idx[0]:lon_idx[-1]+1].values.astype(np.float64)
    ds.close()

# Determine sea cells: finite on every target day
sea_cells = np.all(np.isfinite(target_sst), axis=0)
print(f"Sea cells: {sea_cells.sum()} out of {sea_cells.size}")
print(f"NaN pattern:")
print(f"  Total NaN values across all target days: {np.isnan(target_sst).sum()}")
